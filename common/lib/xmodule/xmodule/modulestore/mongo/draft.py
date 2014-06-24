"""
A ModuleStore that knows about a special version DRAFT. Modules
marked as DRAFT are read in preference to modules without the DRAFT
version by this ModuleStore (so, access to i4x://org/course/cat/name
returns the i4x://org/course/cat/name@draft object if that exists,
and otherwise returns i4x://org/course/cat/name).
"""

import pymongo

from xmodule.exceptions import InvalidVersionError, InvalidBranchSetting
from xmodule.modulestore import PublishState
from xmodule.modulestore.exceptions import ItemNotFoundError, DuplicateItemError
from xmodule.modulestore.mongo.base import (
    MongoModuleStore, as_draft, as_published,
    DIRECT_ONLY_CATEGORIES, DRAFT, PUBLISHED, DRAFT_ONLY, PUBLISHED_ONLY, ALL_REVISIONS,
    SORT_REVISION_FAVOR_DRAFT
)
from opaque_keys.edx.locations import Location


def wrap_draft(item):
    """
    Cleans the item's location and sets the `is_draft` attribute if needed.

    Sets `item.is_draft` to `True` if the item is DRAFT, and `False` otherwise.
    Sets the item's location to the non-draft location in either case.
    """
    setattr(item, 'is_draft', item.location.revision == DRAFT)
    item.location = item.location.replace(revision=None)
    return item


class DraftModuleStore(MongoModuleStore):
    """
    This mixin modifies a modulestore to give it draft semantics.
    Edits made to units are stored to locations that have the revision DRAFT.
    Reads are first read with revision DRAFT, and then fall back
    to the baseline revision only if DRAFT doesn't exist.

    This module also includes functionality to promote DRAFT modules (and their children)
    to published modules.
    """

    def __init__(self, *args, **kwargs):
        """
        Args:
            branch_setting_func: a function that returns the branch setting to use for this store's operations
        """
        super(DraftModuleStore, self).__init__(*args, **kwargs)
        self.branch_setting_func = kwargs.pop('branch_setting_func', PUBLISHED)

    def get_item(self, usage_key, depth=0, revision=None):
        """
        Returns an XModuleDescriptor instance for the item at usage_key.

        Args:
            usage_key: A :class:`.UsageKey` instance

            depth (int): An argument that some module stores may use to prefetch
                descendants of the queried modules for more efficient results later
                in the request. The depth is counted in the number of calls to
                get_children() to cache.  None indicates to cache all descendants.

            revision:
                if PUBLISHED_ONLY, returns only the published item.
                else if DRAFT_ONLY, returns only the draft item.
                else if None, uses the branch setting as follows:
                    if the branch setting is PUBLISHED, returns only the published item.
                    if the branch setting is DRAFT, returns either draft or published item, preferring draft.

                Note: If the item is in DIRECT_ONLY_CATEGORIES, then returns only the PUBLISHED
                version regardless of the revision.

        Raises:
            xmodule.modulestore.exceptions.InsufficientSpecificationError
            if any segment of the usage_key is None except revision

            xmodule.modulestore.exceptions.ItemNotFoundError if no object
            is found at that usage_key
        """
        def get_published():
            return wrap_draft(super(DraftModuleStore, self).get_item(usage_key, depth=depth))

        def get_draft():
            return wrap_draft(super(DraftModuleStore, self).get_item(as_draft(usage_key), depth=depth))

        # return the published version if PUBLISHED-ONLY is requested
        if revision == PUBLISHED_ONLY:
            return get_published()

        # if the item is direct-only, there can only be a published version
        elif usage_key.category in DIRECT_ONLY_CATEGORIES:
            return get_published()

        # return the draft version (without any fallback to PUBLISHED) if DRAFT-ONLY is requested
        elif revision == DRAFT_ONLY:
            return get_draft()

        elif self.branch_setting_func() == PUBLISHED:
            return get_published()
        else:
            try:
                # first check for a draft version
                return get_draft()
            except ItemNotFoundError:
                # otherwise, fall back to the published version
                return get_published()

    def has_item(self, usage_key, revision=None):
        """
        Returns True if location exists in this ModuleStore.

        Args:
            revision:
                if PUBLISHED_ONLY, checks only for the published item
                else if DRAFT_ONLY, checks only for the draft item
                else if None, uses the branch setting, as follows:
                    if the branch setting is PUBLISHED, checks only for the published item
                    if the branch setting is DRAFT, checks whether draft or published item exists
        """
        def has_published():
            return super(DraftModuleStore, self).has_item(usage_key)

        def has_draft():
            return super(DraftModuleStore, self).has_item(as_draft(usage_key))

        if revision == PUBLISHED_ONLY:
            return has_published()
        elif revision == DRAFT_ONLY:
            return has_draft()
        elif self.branch_setting_func() == PUBLISHED:
            return has_published()
        else:
            return has_draft()

    def _get_raw_parent_locations(self, location, revision):
        """
        Get the parents but don't unset the revision in their locations.

        Intended for internal use but not restricted.

        Args:
            location (CourseKey): assumes the location's revision is None; so, uses revision keyword solely
            revision ('draft', 'published', 'all'): if 'draft', only get the draft's parents. etc.
        """
        assert location.revision is None

        # create a query to find all items in the course that have the given location listed as a child
        query = self._course_key_to_son(location.course_key)
        query['definition.children'] = location.to_deprecated_string()

        # find all the items that satisfy the query
        items = self.collection.find(query, {'_id': True}, sort=[('revision', SORT_REVISION_FAVOR_DRAFT)])

        # return only the items that satisfy the request
        return [
            Location._from_deprecated_son(item['_id'], location.course_key.run)
            for item in items
            if (
                # return all versions of the item if revision is 'all'
                revision == 'all' or
                # return this item if it's direct-only and skip the check to compare the revision
                # if the parent is direct-only, always return it, regardless of which revision is requested
                item['_id']['category'] in DIRECT_ONLY_CATEGORIES or
                # return this item only if its revision matches the requested one
                item['_id']['revision'] == revision
            )
        ]

    def get_parent_location(self, location, revision=None, **kwargs):
        '''
        Returns the given location's parent location in this course.

        Returns: version agnostic locations (revision always None) as per the rest of mongo.

        Args:
            revision (None or DRAFT): whether to limit to only parents of the draft.
                If set and if the draft has a different parent than the published, it only returns
                the draft's parent. Because parent's don't record their children's revisions, this
                is actually a potentially fragile deduction based on parent type. If the parent type
                is not DIRECT_ONLY, then the parent revision must be 'draft'.
                Only xml_exporter currently uses this argument. Others should avoid it.
        '''
        if revision is None:
            revision = self.branch_setting_func()
        return super(DraftModuleStore, self).get_parent_location(location, revision, **kwargs)

    def create_xmodule(self, location, definition_data=None, metadata=None, runtime=None, fields={}):
        """
        Create the new xmodule but don't save it. Returns the new module with a draft locator if
        the category allows drafts. If the category does not allow drafts, just creates a published module.

        :param location: a Location--must have a category
        :param definition_data: can be empty. The initial definition_data for the kvs
        :param metadata: can be empty, the initial metadata for the kvs
        :param runtime: if you already have an xmodule from the course, the xmodule.runtime value
        :param fields: a dictionary of field names and values for the new xmodule
        """
        self._verify_branch_setting(DRAFT)

        if location.category not in DIRECT_ONLY_CATEGORIES:
            location = as_draft(location)
        return super(DraftModuleStore, self).create_xmodule(location, definition_data, metadata, runtime, fields)

    def get_items(self, course_key, settings=None, content=None, revision=None, **kwargs):
        """
        Performance Note: This is generally a costly operation, but useful for wildcard searches.

        Returns:
            list of XModuleDescriptor instances for the matching items within the course with
            the given course_key

        NOTE: don't use this to look for courses as the course_key is required. Use get_courses instead.

        Args:
            course_key (CourseKey): the course identifier
            settings: not used
            content: not used
            revision:
                if PUBLISHED_ONLY, returns only Published items
                else if DRAFT_ONLY, returns only Draft items
                else if None, uses the branch setting, as follows:
                    if the branch setting is PUBLISHED, returns only Published items
                    if the branch setting is DRAFT, returns both Draft and Published, but preferring Draft items.
            kwargs (key=value): what to look for within the course.
                Common qualifiers are ``category`` or any field name. if the target field is a list,
                then it searches for the given value in the list not list equivalence.
                Substring matching pass a regex object.
                ``name`` is another commonly provided key (Location based stores)
        """
        def base_get_items(revision):
            return super(DraftModuleStore, self).get_items(course_key, revision=revision, **kwargs)

        def draft_items():
            return [wrap_draft(item) for item in base_get_items(revision=DRAFT)]

        def published_items(draft_items):
            # filters out items that are not already in draft_items
            draft_items_locations = {item.location for item in draft_items}
            return [
                item for item in
                base_get_items(revision=None)
                if item.location not in draft_items_locations
            ]

        if revision == PUBLISHED_ONLY:
            return published_items([])
        elif revision == DRAFT_ONLY:
            return draft_items()
        elif self.branch_setting_func() == PUBLISHED:
            return published_items([])
        else:
            draft_items = draft_items()
            return draft_items + published_items(draft_items)

    def convert_to_draft(self, location, user_id):
        """
        Copy the subtree rooted at source_location and mark the copies as draft.

        Args:
            location: the location of the source (its revision must be None)
            user_id: the ID of the user doing the operation

        Raises:
            InvalidVersionError: if the source can not be made into a draft
            ItemNotFoundError: if the source does not exist
            DuplicateItemError: if the source or any of its descendants already has a draft copy
        """
        return self._convert_to_draft(self, location, user_id)

    def _convert_to_draft(self, location, user_id, delete_published=False, ignore_if_draft=False):
        """
        Internal method with additional internal parameters to convert a subtree to draft.

        Args:
            location: the location of the source (its revision must be None)
            user_id: the ID of the user doing the operation
            delete_published (Boolean): intended for use by unpublish
            ignore_if_draft(Boolean): for internal use only as part of depth first change

        Raises:
            InvalidVersionError: if the source can not be made into a draft
            ItemNotFoundError: if the source does not exist
            DuplicateItemError: if the source or any of its descendants already has a draft copy
        """
        def _internal_depth_first(item):
            """
            Convert the subtree
            """
            # delete the children first
            for child in item.get('definition', {}).get('children', []):
                child_loc = Location.from_deprecated_string(child)
                child_entry = self.collection.find_one({'_id': child_loc.to_deprecated_son()})
                if not child_entry:
                    raise ItemNotFoundError(child_loc)
                _internal_depth_first(child_entry)

            # insert a new DRAFT version of the item
            item['_id']['revision'] = DRAFT
            # ensure keys are in fixed and right order before inserting
            item['_id'] = self._id_dict_to_son(item['_id'])
            try:
                self.collection.insert(item)
            except pymongo.errors.DuplicateKeyError:
                # prevent re-creation of DRAFT versions, unless explicitly requested to ignore
                if not ignore_if_draft:
                    raise DuplicateItemError(item['_id'], self, 'collection')

            # delete the old PUBLISHED version if requested
            if delete_published:
                item['_id']['revision'] = None
                self.collection.remove({'_id': item['_id']})

        # verify input conditions
        self._verify_branch_setting(DRAFT)

        # ensure we are not creating a DRAFT of an item that is direct-only
        if location.category in DIRECT_ONLY_CATEGORIES:
            raise InvalidVersionError(location)

        # find the original (published) item
        original = self.collection.find_one({'_id': location.to_deprecated_son()})
        if not original:
            raise ItemNotFoundError(location)

        # convert the subtree using the original item as the root
        _internal_depth_first(original)

        # refresh our inheritance cache
        self.refresh_cached_metadata_inheritance_tree(location.course_key)

        # return the new draft item
        return wrap_draft(self._load_items(location.course_key, [original])[0])

    def update_item(self, xblock, user_id=None, allow_not_found=False, force=False, isPublish=False):
        """
        See superclass doc.
        In addition to the superclass's behavior, this method converts the unit to draft if it's not
        direct-only and not already draft.
        """
        self._verify_branch_setting(DRAFT)

        # if the xblock is direct-only, update the PUBLISHED version
        if xblock.location.category in DIRECT_ONLY_CATEGORIES:
            return super(DraftModuleStore, self).update_item(xblock, user_id, allow_not_found)

        draft_loc = as_draft(xblock.location)
        try:
            if not super(DraftModuleStore, self).has_item(draft_loc):
                # ignore any descendants which are already draft
                self._convert_to_draft(xblock.location, user_id, ignore_if_draft=True)
        except ItemNotFoundError:
            if not allow_not_found:
                raise

        xblock.location = draft_loc
        super(DraftModuleStore, self).update_item(xblock, user_id, allow_not_found, isPublish)
        return wrap_draft(xblock)

    def delete_item(self, location, user_id, revision=None, **kwargs):
        """
        Delete an item from this modulestore.
        The method determines which revisions to delete. It disconnects and deletes the subtree.
        In general, it assumes deletes only occur on drafts except for direct_only. The only exceptions
        are internal calls like deleting orphans (during publishing as well as from delete_orphan view).
        To signal such pass the keyword revision='all' which makes it clear that all should go away.

        * Deleting a DIRECT_ONLY_CATEGORIES block, deletes both draft and published children and removes from parent.
        * Deleting a specific version of block whose parent is of DIRECT_ONLY_CATEGORIES, only removes it from parent if
        the other version of the block does not exist. Deletes only children of same version.
        * Other deletions remove from parent of same version and subtree of same version

        Args:
            location: UsageKey of the item to be deleted
            user_id: id of the user deleting the item
            revision:
                only provided by contentstore.views.item.orphan_handler
                if None, deletes the item and its subtree, and updates the parents per description above
                if PUBLISHED_ONLY, removes only Published versions
                if 'all', removes both Draft and Published parents
        """
        self._verify_branch_setting(DRAFT)

        direct_only_root = location.category in DIRECT_ONLY_CATEGORIES
        if direct_only_root or revision == PUBLISHED_ONLY:
            parent_revision = PUBLISHED
        elif revision == 'all':
            parent_revision = 'all'
        else:
            parent_revision = DRAFT

        # remove subtree from its parent
        parents = self._get_raw_parent_locations(location, revision=parent_revision)
        # 2 parents iff root has draft which was moved or revision=='all' and parent is draft & pub'd
        for parent in parents:
            # don't remove from direct_only parent if other version of this still exists
            if not direct_only_root and parent.category in DIRECT_ONLY_CATEGORIES:
                # see if other version of root exists
                alt_location = location.replace(revision=DRAFT if location.revision != DRAFT else None)
                if super(DraftModuleStore, self).has_item(alt_location):
                    continue
            parent_block = super(DraftModuleStore, self).get_item(parent, 0)
            parent_block.children.remove(as_published(location))
            parent_block.location = parent  # if the revision is supposed to be draft, ensure it is
            self.update_item(parent_block, user_id)

        if direct_only_root or revision == ALL_REVISIONS:
            as_functions = [as_draft, as_published]
        elif revision == PUBLISHED_ONLY:
            as_functions = [as_published]
        else:
            as_functions = [as_draft]
        self._delete_subtree(location, as_functions)

    def _delete_subtree(self, location, as_functions):
        """
        Internal method for deleting all of the subtree whose revisions match the as_functions
        """
        # now do hierarchical removal
        def _internal_depth_first(current_loc):
            """
            Depth first deletion of nodes
            """
            for rev_func in as_functions:
                current_loc = rev_func(current_loc)
                current_son = current_loc.to_deprecated_son()
                current_entry = self.collection.find_one({'_id': current_son})
                if current_entry is None:
                    continue  # already deleted or not in this version
                for child_loc in current_entry.get('definition', {}).get('children', []):
                    child_loc = current_loc.course_key.make_usage_key_from_deprecated_string(child_loc)
                    _internal_depth_first(child_loc)
                # if deleting both pub and draft and this is direct cat, it will go away
                # in first iteration, but that's ok as all of its children are already gone
                self.collection.remove({'_id': current_son}, safe=self.collection.safe)

        _internal_depth_first(location)
        # recompute (and update) the metadata inheritance tree which is cached
        self.refresh_cached_metadata_inheritance_tree(location.course_key)

    def has_changes(self, location):
        """
        Check if the xblock has been changed since it was last published.
        :param location: location to check
        :return: True if the draft and published versions differ
        """

        # Direct only categories can never have changes because they can't have drafts
        if location.category in DIRECT_ONLY_CATEGORIES:
            return False

        draft = self.get_item(location)

        # If the draft was never published, then it clearly has unpublished changes
        if not draft.published_date:
            return True

        # edited_on may be None if the draft was last edited before edit time tracking
        # If the draft does not have an edit time, we play it safe and assume there are differences
        if draft.edited_on:
            return draft.edited_on > draft.published_date
        else:
            return True

    def publish(self, location, user_id):
        """
        Publish the subtree rooted at location to the live course and remove the drafts.
        Such publishing may cause the deletion of previously published but subsequently deleted
        child trees. Overwrites any existing published xblocks from the subtree.

        Treats the publishing of non-draftable items as merely a subtree selection from
        which to descend.

        Raises:
            ItemNotFoundError: if any of the draft subtree nodes aren't found
        """
        self._verify_branch_setting(DRAFT)

        def _internal_depth_first(root_location):
            """
            Depth first publishing from root
            """
            draft = self.get_item(root_location)

            if draft.has_children:
                for child_loc in draft.children:
                    _internal_depth_first(child_loc)

            if root_location.category in DIRECT_ONLY_CATEGORIES or not getattr(draft, 'is_draft', False):
                # ignore noop attempt to publish something that can't be or isn't currently draft
                return

            try:
                original_published = super(DraftModuleStore, self).get_item(root_location)
            except ItemNotFoundError:
                original_published = None

            if draft.has_children:
                if original_published is not None:
                    # see if previously published children were deleted. 2 reasons for children lists to differ:
                    #   1) child deleted
                    #   2) child moved
                    for child in original_published.children:
                        if child not in draft.children:
                            # did child move?
                            parent = self.get_parent_location(child)
                            if parent == root_location:
                                # deleted from draft; so, delete published now that we're publishing
                                self._delete_subtree(root_location, [as_published])

            super(DraftModuleStore, self).update_item(draft, user_id, isPublish=True)
            self.collection.remove({'_id': as_draft(root_location).to_deprecated_son()})

        _internal_depth_first(location)
        return self.get_item(as_published(location))

    def unpublish(self, location, user_id):
        """
        Turn the published version into a draft, removing the published version.

        NOTE: unlike publish, this gives an error if called above the draftable level as it's intended
        to remove things from the published version
        """
        self._verify_branch_setting(DRAFT)
        return self._convert_to_draft(location, user_id, delete_published=True)

    def _query_children_for_cache_children(self, course_key, items):
        # first get non-draft in a round-trip
        to_process_non_drafts = super(DraftModuleStore, self)._query_children_for_cache_children(course_key, items)

        to_process_dict = {}
        for non_draft in to_process_non_drafts:
            to_process_dict[Location._from_deprecated_son(non_draft["_id"], course_key.run)] = non_draft

        if self.branch_setting_func() == DRAFT:
            # now query all draft content in another round-trip
            query = []
            for item in items:
                item_usage_key = course_key.make_usage_key_from_deprecated_string(item)
                if item_usage_key.category not in DIRECT_ONLY_CATEGORIES:
                    query.append(as_draft(item_usage_key).to_deprecated_son())
            if query:
                query = {'_id': {'$in': query}}
                to_process_drafts = list(self.collection.find(query))

                # now we have to go through all drafts and replace the non-draft
                # with the draft. This is because the semantics of the DraftStore is to
                # always return the draft - if available
                for draft in to_process_drafts:
                    draft_loc = Location._from_deprecated_son(draft["_id"], course_key.run)
                    draft_as_non_draft_loc = draft_loc.replace(revision=None)

                    # does non-draft exist in the collection
                    # if so, replace it
                    if draft_as_non_draft_loc in to_process_dict:
                        to_process_dict[draft_as_non_draft_loc] = draft

        # convert the dict - which is used for look ups - back into a list
        queried_children = to_process_dict.values()

        return queried_children

    def compute_publish_state(self, xblock):
        """
        Returns whether this xblock is 'draft', 'public', or 'private'.

        'draft' content is in the process of being edited, but still has a previous
            version deployed to LMS
        'public' content is locked and deployed to LMS
        'private' content is editable and not deployed to LMS
        """
        if getattr(xblock, 'is_draft', False):
            published_xblock_location = as_published(xblock.location)
            published_item = self.collection.find_one(
                {'_id': published_xblock_location.to_deprecated_son()}
            )
            if published_item is None:
                return PublishState.private
            else:
                return PublishState.draft
        else:
            return PublishState.public

    def _verify_branch_setting(self, expected_branch_setting):
        actual_branch_setting = self.branch_setting_func()
        if actual_branch_setting != expected_branch_setting:
            raise InvalidBranchSetting(
                expected_setting=expected_branch_setting,
                actual_setting=actual_branch_setting
            )
