# Feed Mailer

A commandline application which can send rss feeds to your email

## Usage

### Add Subscription

Subscribe a user to a feed. By default, the email comes from `~/.feedmailer/feedmailer.cfg` but can be overridden by using the email flag.

``` bash
feed-mailer add https://www.phoronix.com/rss.php --title "Phoronix"
```

**Configuration options**

+ `--email` <email> override default email
+ `--title` <title> title of feed
+ `--digest` enable digest of feed instead individual entries. Default is false


### List Subscriptions

Show what feeds users are subscribed to. The numbers listed are the `subscription_id`.

``` bash
feedmailer list
```

``` bash
1. Phoronix -> user@mail.com
```

### List Feeds

Show all feeds that feedmailer knows about. This is useful for commands which require a `feed_id` such as the `refresh` command.

``` bash
feedmailer list-feeds
```

``` bash
1. Phoronix
```

### Remove Subscription

Remove subscription from feedmailer. The id of the subscription can be found using the `list` command.

``` bash
feed-mailer remove <id>
```

### Refresh feeds

Download latest articles for feeds and store them for mailing at some point

**IMPORTANT** This command must be ran regularly in order for the `deliver` command to work otherwise the `deliver` command will never find any articles to deliver

`feed-mailer refresh`

``` bash
feed-mailer refresh <id>
```

### Deliver Emails

``` bash
feed-mailer deliver <ids>
```

**Configuration flags**

+ `--pretend` Show which items would be mailed without actually mailing them

## Configuration

When feed-mailer is first ran, it will create a default configuration file in `~/.feedmailer/feedmailer.cfg`. Below is example configuration with default values.

``` ini
[DEFAULT]
# Default email to use for subscriptions.
# This is required when adding a feed unless the `--email` is used
email =

# Enables digest mode for subscription. Instead of sending out articles as
# individual emails, one email is sent containing all new articles found
digest=No

# Host of the smtp server
smtp_host=

# Port to use to connect to the smtp server
smtp_port=25

# Decides whether to use ssl encryption for communicating with the smtp server
smtp_ssl=No

# Determines whether the smtp server requires authentication
smtp_auth=No

# Login credentials to use when the server requires authentication
smtp_user=
smtp_password=
```

## Scheduling

Manually running commands to refresh and deliver feeds is tedious. It's easier to schedule feedmailer commands to run at certain time intervals.

For those on linux systems, `cron` suits our purposes for scheduling time based tasks.

### Adding Cron Jobs

1. Edit cron tasks for current user

    ``` bash
    crontab -e
    ```

2. Add an entry for refreshing feeds. This entry runs the refresh command every 6 hours

    ``` cron
    0 */6 * * *  feedmailer refresh
    ```

3. Also add an entry for delivering emails for a subscription. The entry below would deliver emails at 4am every day.

    ``` cron
    0 4 * * * feedmail deliver 1
    ```
