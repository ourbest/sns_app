from django.conf.urls import url

from backend import apis, users, zhiyue, tasks, daemons, bot_apis, stats, exts

app_name = 'backend'
urlpatterns = [
    url(r'^ext/stat', exts.daily_stat),

    url(r'^upload$', apis.upload),
    url(r'^task$', apis.task),
    url(r'^url$', apis.redirect),
    url(r'^report$', apis.report_progress),
    url(r'^result$', apis.report_result),
    url(r'^daily/report$', stats.gen_daily_report),
    # url(r'^image$', apis.image),
    url(r'^qr$', bot_apis.login_qr),
    url(r'^qr/status$', bot_apis.get_qr_status),
    url(r'^menu$', apis.get_menu),
    url(r'^tags$', apis.tag_names),

    url(r'^perm/save$', apis.save_perm),

    # imports ====
    url(r'^import/qq$', apis.import_qq),
    # url(r'^import/split$', apis.import_split),
    url(r'^import/user$', apis.import_user),
    url(r'^import/qun$', apis.import_qun),
    url(r'^import/stat$', apis.import_qun_stat),
    url(r'^import/useless_qun$', apis.import_useless_qun),
    url(r'^import/phone$', apis.import_phone),
    url(r'^import/split$', apis.import_qun_split),
    url(r'^import/join$', apis.import_qun_join),

    # my ====
    url(r'^my/qq$', apis.my_qq),
    url(r'^my/qun/cnt$', apis.my_qun_cnt),
    url(r'^my/qun$', apis.my_qun),
    url(r'^my/pending/qun$', apis.my_pending_qun),
    url(r'^my/pending/purge$', apis.my_pending_purge),
    url(r'^my/pending/rearrange$', apis.my_pending_rearrange),
    url(r'^my/quiz/qun$', apis.my_quiz_qun),
    url(r'^my/qun/lost$', apis.my_lost_qun),
    url(r'^my/tasks$', apis.my_tasks),
    url(r'^my/apply/log$', apis.my_apply_log),
    url(r'^my/qun/attr$', apis.update_user_group_attr),
    url(r'^my/online$', apis.online_phones),
    url(r'^my/kicked$', apis.my_kicked_qun),
    url(r'^my/pending/remove$', apis.my_pending_remove),
    url(r'^my/majia$', apis.user_majia),
    url(r'^my/majia/add$', apis.add_user_majia),
    url(r'^my/majia/type$', users.update_majia_type),
    url(r'^my/majia/remove$', users.remove_majia),

    url(r'^device/qun$', apis.device_qun),
    url(r'^device/create$', apis.device_create),
    url(r'^device/tasks$', apis.device_tasks),
    url(r'^device/articles$', apis.device_articles),
    url(r'^device/update/attr$', apis.update_device_attr),
    url(r'^device/transfer$', apis.device_transfer),

    url(r'^qq/create$', apis.qq_create),
    url(r'^qq/provider$', apis.update_qq_provider),
    url(r'^qq/pwd$', apis.get_qq_password),

    url(r'^qq/drop$', apis.qq_drop),

    url(r'^split/qq$', apis.split_qq),
    url(r'^users$', apis.users),
    url(r'^devices$', apis.devices),
    url(r'^accounts$', apis.accounts),
    url(r'^account/info$', apis.account),
    url(r'^account/update$', apis.update_account),
    url(r'^account/update/attr$', apis.update_account_attr),
    url(r'^account/transfer$', apis.qq_transfer),
    url(r'^account/qun$', apis.account_qun),
    url(r'^split/phone/qq$', apis.split_qun_to_device),
    url(r'^reset/phone/qq$', apis.reset_phone_split),
    url(r'^qun$', apis.export_qun),
    url(r'^export/qun$', apis.export_qun_csv),
    url(r'^send/qq$', apis.send_qq),
    url(r'^login/submit$', apis.login),
    url(r'^login/info$', apis.login_info),
    url(r'^logout$', apis.logout),
    url(r'^apps$', apis.apps),
    url(r'^app/summary$', apis.app_summary),
    url(r'^task/types$', apis.task_types),
    url(r'^task/data$', apis.task_data),
    url(r'^task/update/status$', apis.update_task_status),
    url(r'^task/create$', apis.create_task),
    url(r'^task/devices$', apis.task_devices),
    url(r'^task/files$', apis.task_files),
    url(r'^task/groups$', apis.task_groups),
    url(r'^file/content$', apis.file_content),
    url(r'^task/logs$', tasks.work_logs),
    url(r'^image$', apis.file_content),
    url(r'^user/info$', users.user_info),
    url(r'^user/update$', users.update_user_info),
    url(r'^user/pwd$', users.change_password),
    url(r'^user/all$', users.all_users),
    url(r'^user/delegates$', users.delegates),
    url(r'^user/delegated$', users.delegated),
    url(r'^user/delegate/update$', users.set_delegates),

    url(r'^article/attr$', apis.set_article_attr),

    url(r'^share/items$', apis.get_share_items),

    # ===team
    url(r'^team/devices$', apis.team_devices),
    url(r'^team/qq$', apis.team_qq),
    url(r'^team/qun$', apis.team_qun),
    url(r'^team/tasks$', apis.team_tasks),
    url(r'^team/article/dist$', apis.team_dist_info),
    url(r'^team/users$', apis.team_users),
    url(r'^team/summary/qun$', apis.sum_team_qun),
    url(r'^team/summary/dist$', zhiyue.sum_team_dist),
    url(r'^team/articles$', stats.team_articles),

    url(r'^tmp$', apis.temp_func),
    url(r'^import/result$', apis.re_import),

    ##### zhiyue
    url(r'^zhiyue/share$', zhiyue.user_share),
    url(r'^zhiyue/title$', zhiyue.get_url_title),
    url(r'^zhiyue/stat$', zhiyue.count_user_sum),
    url(r'^zhiyue/majia$', zhiyue.get_user_majia),
    url(r'^zhiyue/link$', zhiyue.show_open_link),

    url(r'^zhiyue/report$', zhiyue.app_report),
    url(r'^zhiyue/report/user$', zhiyue.app_report_user),
    url(r'^zhiyue/active$', zhiyue.get_app_stat),
    url(r'^zhiyue/new$', zhiyue.get_new_device),
    url(r'^zhiyue/active/days$', zhiyue.get_stat_before_days),
    url(r'^zhiyue/active/detail$', zhiyue.get_active_detail),

    # internal
    url(r'^change/ver$', apis.change_js_version),
    url(r'^daemon/check$', daemons.check_online_task),
    url(r'^daemon/stat$', daemons.daily_stat),
    url(r'^daemon/stat/save$', daemons.save_daily_active),
    url(r'^daemon/stat/article$', stats.get_item_stat_values),

    # weixin
    url(r'^wx/contact/sync$', bot_apis.sync_contacts),
    url(r'^wx/contacts$', bot_apis.get_contacts),

    # coupon
    url(r'coupon/users$', zhiyue.get_offline_ids),
    url(r'coupon/detail$', zhiyue.get_coupon_details),
]
