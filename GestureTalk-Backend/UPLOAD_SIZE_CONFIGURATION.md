# Upload Size Configuration Guide

## Problem: 413 Payload Too Large Error

When uploading large video files, you may encounter a 413 error. This happens when the request size exceeds server limits.

## Current Configuration (Testing Mode)

**Note:** The system is currently configured for **TESTING MODE** with very high limits to allow large video files during development.

### 1. Apache Server (.htaccess) - Already Configured

The `.htaccess` file in `public/.htaccess` has been configured for testing with:
```apache
php_value upload_max_filesize 1000M
php_value post_max_size 1000M
php_value max_execution_time 600
php_value max_input_time 600
php_value memory_limit 512M
```

**For Production:** Reduce these limits to more reasonable values (e.g., 200M for upload_max_filesize).

**Note:** These settings only work if PHP is running as an Apache module. If you're using PHP-FPM, you need to configure PHP directly.

### 2. PHP Configuration (php.ini)

If using PHP-FPM or if .htaccess doesn't work, update your `php.ini` file:

**Testing Mode (Current):**
```ini
upload_max_filesize = 1000M
post_max_size = 1000M
max_execution_time = 600
max_input_time = 600
memory_limit = 512M
```

**Production Mode (Recommended):**
```ini
upload_max_filesize = 200M
post_max_size = 200M
max_execution_time = 300
max_input_time = 300
memory_limit = 256M
```

**Location of php.ini:**
- Windows: Usually in `C:\php\php.ini` or `C:\xampp\php\php.ini`
- Linux: Usually in `/etc/php/8.x/fpm/php.ini` or `/etc/php/8.x/apache2/php.ini`
- macOS: Usually in `/usr/local/etc/php/8.x/php.ini`

After changing php.ini, restart your web server:
- Apache: `sudo service apache2 restart` or restart XAMPP/WAMP
- PHP-FPM: `sudo service php8.x-fpm restart`
- Laravel: `php artisan serve` (restart the server)

### 3. Nginx Configuration

If using Nginx, add to your server block in `/etc/nginx/sites-available/your-site`:

**Testing Mode (Current):**
```nginx
server {
    client_max_body_size 1000M;
    client_body_timeout 600s;
    
    # ... rest of your configuration
}
```

**Production Mode (Recommended):**
```nginx
server {
    client_max_body_size 200M;
    client_body_timeout 300s;
    
    # ... rest of your configuration
}
```

Then restart Nginx:
```bash
sudo nginx -t  # Test configuration
sudo service nginx restart
```

### 4. Laravel Configuration

**Testing Mode (Current):** The Laravel validation limit has been set to 1000MB in `TranslationController.php`:
```php
'input_data' => 'nullable|file|mimes:mp4,jpg,jpeg,png|max:1000000',
```

**Production Mode (Recommended):** Reduce to:
```php
'input_data' => 'nullable|file|mimes:mp4,jpg,jpeg,png|max:200000',
```

### 5. Verify Configuration

Check your PHP settings by creating a test file `info.php`:
```php
<?php
phpinfo();
?>
```

Look for:
- `upload_max_filesize` - should be 1000M (testing) or 200M (production)
- `post_max_size` - should be 1000M (testing) or 200M (production) (must be >= upload_max_filesize)
- `max_execution_time` - should be 600 (testing) or 300 (production)
- `memory_limit` - should be 512M (testing) or 256M (production)

**Important:** `post_max_size` must be equal to or larger than `upload_max_filesize`.

### 6. Fallback Behavior

If the video file is too large, the app will automatically:
1. Detect the 413 error
2. Save the translation without the video file
3. Show a message: "Video file is too large for upload. Saving translation without video file..."

The translation will still be saved with:
- ✅ Translation text
- ✅ Audio file (if generated)
- ❌ Video file (skipped due to size)

## Troubleshooting

1. **Still getting 413 error?**
   - Check if PHP-FPM is being used (php.ini changes needed)
   - Check web server logs for exact error
   - Verify `post_max_size >= upload_max_filesize`

2. **Changes not taking effect?**
   - Restart web server
   - Clear Laravel cache: `php artisan config:clear`
   - Check which php.ini is being used: `php --ini`

3. **Need larger files?**
   - Increase limits in all three places: php.ini, .htaccess, and Laravel validation
   - Consider using chunked uploads for very large files

