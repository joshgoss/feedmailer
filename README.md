# Feed Mailer

A commandline application which can send rss feeds to your email

## Database

**feeds**

``` text
id PRIMARY KEY
title VARCHAR NOT NULL
url VARCHAR NOT NULL
digest BOOLEAN DEFAULT FALSE
max_age INTEGER NULL
created_at TIMESTAMP
checked_at TIMESTAMP NULL
delivered_at TIMESTAMP NULL
```

**items**

``` text
id PRIMARY KEY
title VARCHAR NOT NULL
url VARCHAR NOT NULL
description VARCHAR
content VARCHAR
author VARCHAR
category VARCHAR NULL
published_at VARCHAR
created_at timestamp DEFAULT CURRENT_TIMESTAMP
delivered_at timestamp NULL
```

## Usage

### Add Feed

`feed-mailer add https://www.phoronix.com/rss.php --title "Phoronix"`

**Configuration options**
--title -t  <title> title of feed
--digest -d enable digest of feed instead individual entries. Default is false
--max-age -m <days> only mail entries X days old or younger. Default is 0 (no max age)


### List Feeds

`feed-mailer list`

``` bash
1) Phoronix
```

### Remove Feed

`feed-mailer remove <id>`

### Refresh feeds
Download latest articles for feeds and store them for mailing at some point

`feed-mailer refresh`

`feed-mailer refresh <id>`

### Deliver Emails

`feed-mailer deliver`

`feed-mailer deliver <id>`

**Configuration flags**

-d --dry-run Show which items would be mailed without actually mailing them
