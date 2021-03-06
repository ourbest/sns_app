from django.conf.urls import url

from backend import apis, users, zhiyue, tasks, daemons, bot_apis, stats, exts, kpi, offline, online, channels, shares, \
    onlines, data, tests, qn, charts

app_name = 'backend'
urlpatterns = [
    url(r'^ext/stat', exts.daily_stat),

    url(r'^upload$', apis.upload),
    url(r'^task$', apis.task),
    url(r'^url$', apis.redirect),
    url(r'^item/url$', apis.article),
    url(r'^report$', apis.report_progress),
    url(r'^result$', apis.report_result),
    url(r'^daily/report$', stats.gen_daily_report),
    # url(r'^image$', apis.image),
    url(r'^qr$', bot_apis.login_qr),
    url(r'^qr/status$', bot_apis.get_qr_status),
    url(r'^menu$', apis.get_menu),
    url(r'^tags$', apis.tag_names),

    url(r'^perm/save$', apis.save_perm),

    url(r'^secondary/notice$', apis.secondary_task_notice),
    url(r'^secondary/calling$', apis.request_calling),

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

    url(r'my/following', users.api_my_following),
    url(r'my/follow', users.api_my_follow),

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

    url(r'^split/qq/all$', apis.split_qq_all),
    url(r'^split/qq$', apis.split_qq),
    url(r'^split/qq/users$', apis.split_qq_users),
    url(r'^users$', apis.users),
    url(r'^devices$', apis.devices),
    url(r'^accounts$', apis.accounts),
    url(r'^account/info$', apis.account),
    url(r'^account/update$', apis.update_account),
    url(r'^qun/update/app$', apis.update_qun_app),
    url(r'^qun/update/attr$', apis.update_qun_attr),
    url(r'^account/update/attr$', apis.update_account_attr),
    url(r'^account/transfer$', apis.qq_transfer),
    url(r'^account/qun$', apis.account_qun),
    url(r'^split/phone/qq$', apis.split_qun_to_device),
    url(r'^reset/phone/qq$', apis.reset_phone_split),
    url(r'^qun$', apis.export_qun),
    url(r'^qun/history$', apis.qun_history),
    url(r'^export/qun$', apis.export_qun_csv),
    url(r'^export/user_qun$', apis.export_phone_qun_csv),
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
    url(r'^task/auto$', apis.task_auto_data),
    url(r'^task/item/mark$', apis.api_task_item_mark),

    url(r'^file/content$', apis.file_content),
    url(r'^task/logs$', tasks.work_logs),
    url(r'^image$', apis.file_content),
    url(r'^user/info$', users.user_info),
    url(r'^user/update$', users.update_user_info),
    url(r'^user/disable$', users.disable_user),
    url(r'^user/update/status$', users.update_user_status),
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
    url(r'^team/weixin$', apis.team_weixin),
    url(r'^team/known$', apis.team_known_qun),
    url(r'^team/split$', apis.team_split_qun),
    url(r'^team/tasks$', apis.team_tasks),
    url(r'^team/article/dist$', apis.team_dist_info),
    url(r'^team/users$', apis.team_users),
    url(r'^team/summary/qun$', apis.sum_team_qun),
    url(r'^team/summary/dist$', zhiyue.sum_team_dist),
    url(r'^team/articles$', stats.team_articles),

    url(r'^tmp$', apis.temp_func),
    url(r'^import/result$', apis.re_import),

    # --- zhiyue
    url(r'^zhiyue/share$', zhiyue.user_share),
    url(r'^zhiyue/message/save$', zhiyue.message_save),
    url(r'^zhiyue/messages$', zhiyue.messages),
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
    url(r'^zhiyue/push/stat$', zhiyue.push_audit_stat),
    url(r'^zhiyue/push/items$', zhiyue.push_items),

    url(r'^zhiyue/shorten/list$', zhiyue.shorten_list),
    url(r'^zhiyue/shorten/add', zhiyue.shorten_add),

    # internal
    url(r'^change/ver$', apis.change_js_version),
    url(r'^daemon/check$', daemons.check_online_task),
    url(r'^daemon/stat$', daemons.daily_stat),
    url(r'^daemon/stat/weekly$', daemons.weekly_stat),
    url(r'^daemon/reset_apply$', apis.reset_applying),
    url(r'^daemon/stat/save$', daemons.save_daily_active),
    url(r'^daemon/stat/article$', stats.get_item_stat_values),
    url(r'^daemon/stat/app$', daemons.gauge_data),
    url(r'^daemon/stat/offline$', zhiyue.make_offline),
    url(r'^daemon/stat/off$', zhiyue.make_offline_days),
    url(r'^daemon/stat/sync/user$', zhiyue.sync_user),
    url(r'^daemon/stat/rt/user$', zhiyue.sync_user_realtime),
    url(r'^daemon/stat/pv$', zhiyue.sync_pv),
    url(r'^daemon/backup/weizhan$', daemons.backup_weizhan),

    # weixin
    url(r'^wx/contact/sync$', bot_apis.sync_contacts),
    url(r'^wx/contacts$', bot_apis.get_contacts),

    # coupon
    url(r'^coupon/users$', zhiyue.get_offline_ids),
    url(r'^coupon/detail$', zhiyue.get_coupon_details),
    url(r'^coupon/message/detail$', zhiyue.get_coupon_message_details),
    url(r'^coupon/offline$', zhiyue.get_offline_detail),

    # stat
    url(r'^stat/city$', stats.item_user_loc),
    url(r'^stat/category$', stats.team_category),
    url(r'^stat/remain$', stats.article_remain),
    url(r'^stat/click$', stats.sum_daily_click),

    # kpi
    url(r'^kpi/detail$', kpi.api_kpi),
    url(r'^kpi/config$', kpi.api_kpi_config),
    url(r'^kpi/config/save$', kpi.api_kpi_save),
    url(r'^kpi/config/remove$', kpi.api_kpi_remove),

    # offline
    url(r'^offline/owners$', offline.api_owners),
    url(r'^offline/dates$', offline.api_daily_remain),
    url(r'^offline/detail$', offline.api_app_detail),
    url(r'^offline/owner/remain$', offline.api_owner_remain),
    url(r'^offline/owner/detail$', offline.api_owner_detail),
    url(r'^offline/owner/date$', offline.api_owner_date),
    url(r'^offline/owner/stat$', offline.api_owner_stat),
    url(r'^offline/owner/detail/stat$', offline.api_owner_detail_stat),
    url(r'^offline/report$', offline.daily_report),
    url(r'^offline/withdraw$', offline.api_cash_amount),
    url(r'^offline/weekdays$', offline.api_weekdays),
    url(r'^offline/weekly$', offline.api_weekly_report),
    url(r'^offline/app$', offline.api_offline_app),
    url(r'^offline/check$', offline.api_check_coupon_rate),

    # online
    url(r'^online/owners$', online.api_owners),
    url(r'^online/dates$', online.api_daily_remain),
    url(r'^online/detail$', online.api_app_detail),
    url(r'^online/owner/remain$', online.api_owner_remain),
    url(r'^online/owner/detail$', online.api_owner_detail),
    url(r'^online/owner/date$', online.api_owner_date),
    url(r'^online/heat$', online.api_all_active_users),
    url(r'^online/html$', online.html_heat),

    # active
    url(r'^active/users$', online.api_active_users),

    # channels
    url(r'^channels/stat$', channels.api_channel_stats),
    url(r'^channels/details$', channels.api_channel_details),
    url(r'^channels/names$', channels.api_channel_names),
    url(r'^channels/remain$', channels.api_channel_remain),
    url(r'^channels/config$', channels.api_get_ad_channels),
    url(r'^channels/weekly$', channels.api_weekly_report),
    url(r'^channels/config/save$', channels.api_set_ad_channels),

    # shares
    url(r'^shares/stat$', shares.api_share_stat),
    url(r'^shares/weekly$', shares.api_share_stat_weekly),
    url(r'^shares/details$', shares.api_stat_details),

    # onlines
    url(r'^onlines/stat$', onlines.api_stat),
    url(r'^onlines/today$', onlines.api_today),
    url(r'^onlines/weekly$', onlines.api_weekly),

    # majiang
    url(r'^majiang$', apis.majiang),

    # 图片回掉
    url(r'^img/cb$', zhiyue.qiniu_cb),
    url(r'^mark$', qn.mark_status),

    # data
    url(r'^export/data$', data.export_data),

    # test
    url(r'^test$', tests.test_api),
    # android open item
    url(r'^open/item$', zhiyue.open_item),
    url(r'^qn/img$', qn.show_img),

    # graph
    url(r'^chart/month/data', charts.api_get_app_month_data),
    url(r'^chart/today/data', charts.api_get_app_today),
]
