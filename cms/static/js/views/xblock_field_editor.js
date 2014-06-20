/**
 * FieldEditorView is a view that allows a single value of an xblock to be edited.
 */
define(["jquery", "gettext", "js/views/baseview"],
    function ($, gettext, BaseView) {

        var XBlockFieldEditor = BaseView.extend({
            events: {
                'click .xblock-field-value': 'showInput',
                'change .xblock-field-editor-input': 'updateField',
                'focusout .xblock-field-editor-input': 'hideInput',
                'keyup .xblock-field-editor-input': 'handleKeyUp'
            },

            // takes XBlockInfo as a model

            initialize: function() {
                BaseView.prototype.initialize.call(this);
                this.fieldName = this.$el.data('field');
                this.template = this.loadTemplate('xblock-field-editor');
                this.model.on('change:' + this.fieldName, this.onChangeField, this);
            },

            render: function() {
                this.$el.append(this.template({
                    value: this.model.get(this.fieldName),
                    fieldName: this.fieldName
                }));
                return this;
            },

            onChangeField: function() {
                var value = this.model.get(this.fieldName),
                    label = this.$('.xblock-field-value'),
                    input = this.$('.xblock-field-editor-input');
                label.text(value);
                input.val(value);
            },

            showInput: function(event) {
                var label = this.$('.xblock-field-value'),
                    input = this.$('.xblock-field-editor-input');
                event.preventDefault();
                label.addClass('is-hidden');
                input.removeClass('is-hidden');
                input.focus();
            },

            hideInput: function() {
                var label = this.$('.xblock-field-value'),
                    input = this.$('.xblock-field-editor-input');
                label.removeClass('is-hidden');
                input.addClass('is-hidden');
            },

            updateField: function() {
                var self = this,
                    xblockInfo = this.model,
                    metadata = {},
                    requestData = { metadata: metadata },
                    input = this.$('.xblock-field-editor-input'),
                    fieldName = this.fieldName,
                    newValue = input.val(),
                    url = this.model.urlRoot + '/' + this.model.id;
                metadata[fieldName] = newValue;
                this.runOperationShowingMessage(gettext('Saving&hellip;'),
                    function() {
                        return $.postJSON(url, requestData);
                    }).done(function() {
                        xblockInfo.set(fieldName, newValue);
                    }).always(function() {
                        self.hideInput();
                    });
            },

            handleKeyUp: function(event) {
                var keyCode = event.keyCode,
                    input = this.$('.xblock-field-editor-input');
                if (keyCode === 27) {   // Revert the changes if the user hits cancel
                    input.val(this.model.get(this.fieldName));
                    this.hideInput();
                }
            }
        });

        return XBlockFieldEditor;
    }); // end define();
