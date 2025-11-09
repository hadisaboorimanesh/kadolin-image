def post_init_copy_website_url(cr, registry):
    # یک‌بار: مقدار فعلی website_url را به ستون manual کپی کن
    # اگر ستون manual وجود داشته باشد.
    try:
        cr.execute("""
            UPDATE product_template
               SET website_url_manual = website_url
            WHERE website_url IS NOT NULL
              AND (website_url_manual IS NULL OR website_url_manual = '');
        """)
    except Exception:
        # اگر ستون/فیلد وجود نداشت یا خطایی بود، بی‌صدا رد شو
        pass
