from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from .views import search, home, scrap, search_results, search_submit, site_ban, site_edit, site_content_detail, site_content_edit, site_edit_name, site_edit_category, search_results_all, search_new, search_add, site_add, site_new, sites_edit_category, scrap_site, scrap_product_info, scrap_info_edit_do, scrap_site_edit, scrap_plugin, scrap_site_info, scrap_export, product_ban


urlpatterns = patterns('',
    home.url(),
    search.url(),
    search_add.url(),
    search_new.url(),
    search_results.url(),
    search_results_all.url() ,
    search_submit.url(),
    site_new.url(),
    site_add.url(),
    site_ban.url(),
    site_edit.url(),
    site_edit_name.url(),
    site_edit_category.url(),
    site_content_detail.url(),
    site_content_edit.url(),
    sites_edit_category.url(),
    scrap.url(),
    scrap_site.url(),
    scrap_site_edit.url(),
    scrap_product_info.url(),
    scrap_site_info.url(),
    scrap_info_edit_do.url(),
    scrap_plugin.url(),
    scrap_export.url(),
    product_ban.url(),
)
