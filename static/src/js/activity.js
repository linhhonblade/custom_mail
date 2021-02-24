odoo.define('custom_mail.Activity', function (require) {
    'use strict';

    var CustomActivity = require('mail.Activity');
    CustomActivity.template = 'custom_mail.Activity';
});