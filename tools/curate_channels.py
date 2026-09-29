#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds app/src/main/assets/channels.json from curated, public IPTV sources.

The script expects the upstream playlists next to it (see tools/sources/README.md):

    tools/sources/persian.json   https://github.com/Samhouston010/persian-tv
    tools/sources/news.json      https://github.com/iptv-org/iptv (categories/news.m3u)
    tools/sources/music.json     https://github.com/iptv-org/iptv (categories/music.m3u)
    tools/sources/sports.json    https://github.com/iptv-org/iptv (categories/sports.m3u)

Run:  python3 tools/curate_channels.py
"""
import json, os, sys, datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')
def load(f):
    return json.load(open(os.path.join(DATA, f), encoding='utf-8'))

SRC = {
    'persian': {c['name']: c for c in load('persian.json')},
    'news': {c['name']: c for c in load('news.json')},
    'music': {c['name']: c for c in load('music.json')},
    'sports': {c['name']: c for c in load('sports.json')},
}

P = 'https://cdn.jsdelivr.net/gh/Samhouston010/persian-tv@master/logos/persiana/'
W = 'https://cdn.jsdelivr.net/gh/Samhouston010/persian-tv@master/logos/'

# (id, fa, en, category, source, key, quality)
TABLE = [
    # ---------------- پرشیانا گروپ ----------------
    ('persiana-family',    'پرشیانا فمیلی',    'Persiana Family',   'persiana', 'persian', 'Family', 'HD'),
    ('persiana-series',    'پرشیانا سریال',    'Persiana Series',   'persiana', 'persian', 'Series', 'HD'),
    ('persiana-cinema',    'پرشیانا سینما',    'Persiana Cinema',   'persiana', 'persian', 'Cinema', 'HD'),
    ('persiana-iranian',   'پرشیانا ایرانی',   'Persiana Iranian',  'persiana', 'persian', 'Iranian', 'HD'),
    ('persiana-korea',     'پرشیانا کره',      'Persiana Korea',    'persiana', 'persian', 'Korea', 'HD'),
    ('persiana-plus',      'پرشیانا پلاس',     'Persiana+',         'persiana', 'persian', 'Persiana+', 'HD'),
    ('persiana-comedy',    'پرشیانا کمدی',     'Persiana Comedy',   'persiana', 'persian', 'Comedy', 'HD'),
    ('persiana-reality',   'پرشیانا ریالیتی',  'Persiana Reality',  'persiana', 'persian', 'Reality', 'HD'),
    ('persiana-turkiye',   'پرشیانا ترکیه',    'Persiana Türkiye',  'persiana', 'persian', 'Türkiye', 'HD'),
    ('persiana-medical',   'پرشیانا مدیکال',   'Persiana Medical',  'persiana', 'persian', 'Medical', 'HD'),
    ('persiana-docs',      'پرشیانا مستند',    'Persiana Docs',     'persiana', 'persian', 'Docs', 'HD'),
    ('persiana-junior',    'پرشیانا جونیور',   'Persiana Junior',   'persiana', 'persian', 'Junior', 'HD'),
    ('persiana-fight',     'پرشیانا فایت',     'Persiana Fight',    'persiana', 'persian', 'Fight', 'HD'),
    ('persiana-music',     'پرشیانا موزیک',    'Persiana Music',    'persiana', 'persian', 'Music', 'HD'),
    ('persiana-nostalgia', 'پرشیانا نستالژی',  'Persiana Nostalgia','persiana', 'persian', 'Nostalgia', 'HD'),
    ('persiana-sonati',    'پرشیانا سنتی',     'Persiana Sonnati',  'persiana', 'persian', 'سنتی', 'HD'),
    ('persiana-setmix',    'پرشیانا ست‌میکس',  'Persiana SetMix',   'persiana', 'persian', 'SetMix', 'HD'),
    ('persiana-travel',    'پرشیانا سفر',      'Persiana Travel',   'persiana', 'persian', 'Travel', 'HD'),
    ('persiana-podcast',   'پرشیانا پادکست',   'Persiana Podcast',  'persiana', 'persian', 'Podcast', 'HD'),
    ('persiana-rap',       'پرشیانا رپ',       'Persiana Rap',      'persiana', 'persian', 'Rap', 'HD'),
    ('persiana-china',     'پرشیانا چین',      'Persiana China',    'persiana', 'persian', 'China', 'HD'),
    ('persiana-voyage',    'پرشیانا وویاژ',    'Persiana Voyage',   'persiana', 'persian', 'Voyage', 'HD'),
    ('mbc-persia',         'ام‌بی‌سی پرشیا',   'MBC Persia',        'persiana', 'persian', 'MBC Persia', 'HD'),
    ('fx-tv-1',            'اف‌ایکس تی‌وی ۱',  'FX TV 1',           'persiana', 'persian', 'FX TV 1', 'HD'),
    ('mtc-tv',             'ام‌تی‌سی تی‌وی',   'MTC TV',            'persiana', 'persian', 'MTC TV', 'HD'),
    ('ava-family',         'آوا فمیلی',        'AVA Family',        'persiana', 'persian', 'AVA Family', 'HD'),

    # ---------------- خبری ----------------
    ('bbc-persian',        'بی‌بی‌سی فارسی',   'BBC Persian',       'news', 'persian', 'BBC Persian', 'HD'),
    ('iran-international', 'ایران اینترنشنال','Iran International','news', 'persian', 'Iran International', 'HD'),
    ('voa-persian',        'صدای آمریکا',      'VOA Persian',       'news', 'persian', 'VOA Persian', 'HD'),
    ('radio-farda',        'رادیو فردا',       'Radio Farda TV',    'news', 'persian', 'Radio Farda TV', 'HD'),
    ('simaye-azadi',       'سیمای آزادی',      'Simaye Azadi',      'news', 'persian', 'سیمای آزادی', 'HD'),
    ('al-alam',            'العالم فارسی',     'Al Alam',           'news', 'news', 'Al Alam (360p)', 'SD'),
    ('press-tv',           'پرس تی‌وی',        'Press TV',          'news', 'x', {'url': 'https://live.presstv.ir/hls/presstv.m3u8', 'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fb/Press_TV_logo.svg/960px-Press_TV_logo.svg.png'}, 'HD'),
    ('hispan-tv',          'هیسپان تی‌وی',     'Hispan TV',         'news', 'news', 'Hispan TV', 'HD'),
    ('setareh-tv',         'ستاره تی‌وی',      'Setareh TV',        'news', 'persian', 'Setareh TV', 'HD'),
    ('aljazeera-en',       'الجزیره انگلیسی',  'Al Jazeera English','news', 'persian', 'Al Jazeera English', 'HD'),
    ('aljazeera-ar',       'الجزیره عربی',     'Al Jazeera Arabic', 'news', 'persian', 'Al Jazeera Arabic', 'HD'),
    ('bbc-news',           'بی‌بی‌سی نیوز',    'BBC World News',    'news', 'persian', 'BBC World News', 'HD'),
    ('sky-news',           'اسکای نیوز',       'Sky News',          'news', 'persian', 'Sky News', 'HD'),
    ('cnn',                'سی‌ان‌ان',         'CNN',               'news', 'persian', 'CNN', 'HD'),
    ('cnbc',               'سی‌ان‌بی‌سی',      'CNBC',              'news', 'persian', 'CNBC', 'HD'),
    ('bloomberg',          'بلومبرگ',          'Bloomberg TV+',     'news', 'persian', 'Bloomberg TV+', 'HD'),
    ('dw-english',         'دویچه وله',        'DW English',        'news', 'persian', 'DW English', 'HD'),
    ('france24-en',        'فرانس ۲۴',         'France 24 English', 'news', 'news', 'France 24 English (1080p)', 'HD'),
    ('euronews',           'یورونیوز',         'Euronews English',  'news', 'news', 'Euronews English (720p)', 'HD'),
    ('trt-world',          'تی‌آر‌تی ورلد',    'TRT World',         'news', 'persian', 'TRT World', 'HD'),
    ('cna',                'سی‌ان‌ای',         'CNA',               'news', 'persian', 'CNA', 'HD'),
    ('abc-news-au',        'ای‌بی‌سی استرالیا','ABC News Australia','news', 'persian', 'ABC News Australia', 'HD'),
    ('nbc-news-now',       'ان‌بی‌سی نیوز ناو','NBC News NOW',      'news', 'persian', 'NBC News NOW', 'HD'),
    ('i24news-en',         'آی‌۲۴ نیوز',       'i24NEWS English',   'news', 'news', 'i24NEWS English World (1080p)', 'HD'),
    ('al-arabiya',         'العربیه',          'Al Arabiya',        'news', 'persian', 'Al Arabiya', 'HD'),
    ('sky-news-arabia',    'اسکای نیوز عربی',  'Sky News Arabia',   'news', 'news', 'Sky News Arabia (1080p)', 'HD'),
    ('al-hadath',          'الحدث',            'Al Hadath',         'news', 'persian', 'Al Hadath', 'HD'),
    ('nhk-world',          'ان‌اچ‌کی ژاپن',    'NHK World-Japan',   'news', 'news', 'NHK World-Japan (1080p)', 'HD'),
    ('cgtn',               'سی‌جی‌تی‌ان',      'CGTN',              'news', 'persian', 'CGTN', 'HD'),

    # ---------------- موزیک ----------------
    ('pmc-royale',         'پی‌ام‌سی رویال',   'PMC Royale',        'music', 'persian', 'PMC Royale', 'HD'),
    ('pmc',                'پی‌ام‌سی',         'PMC',               'music', 'persian', 'PMC (Backup)', 'HD'),
    ('radio-javan',        'رادیو جوان',       'Radio Javan TV',    'music', 'persian', 'Radio Javan TV', 'HD'),
    ('avang-tv',           'آونگ تی‌وی',       'Avang TV',          'music', 'persian', 'Avang TV', 'HD'),
    ('navahang',           'نواهنگ',           'Navahang TV',       'music', 'persian', 'Navahang TV', 'HD'),
    ('sun-music',          'سان موزیک',        'Sun Music',         'music', 'persian', 'Sun Music', 'HD'),
    ('t2-tv',              'تی‌۲ تی‌وی',       'T2 TV',             'music', 'persian', 'T2 TV', 'HD'),
    ('4u-tv',              'فور یو تی‌وی',     '4U TV',             'music', 'persian', '4U TV', 'HD'),
    ('biz-music',          'بیز موزیک',        'BIZ Music',         'music', 'persian', 'BIZ Music', 'HD'),
    ('vevo-pop',           'وِوو پاپ',         'Vevo Pop',          'music', 'music', 'Vevo Pop (1080p)', 'HD'),
    ('vevo-90s',           'وِوو دهه ۹۰',      "Vevo '90s",         'music', 'music', "Vevo '90s (1080p)", 'HD'),
    ('vevo-hiphop',        'وِوو هیپ‌هاپ',     'Vevo Hip Hop',      'music', 'music', 'Vevo Hip Hop (1080p)', 'HD'),
    ('vevo-retro-rock',    'وِوو راک کلاسیک',  'Vevo Retro Rock',   'music', 'music', 'Vevo Retro Rock (1080p)', 'HD'),
    ('mtv-biggest-pop',    'ام‌تی‌وی پاپ',     'MTV Biggest Pop',   'music', 'music', 'MTV Biggest Pop (1080p)', 'HD'),
    ('yo-mtv',             'یو! ام‌تی‌وی',     'Yo! MTV',           'music', 'music', 'Yo! MTV (1080p)', 'HD'),
    ('mtv-classic',        'ام‌تی‌وی کلاسیک',  'MTV Classic',       'music', 'music', 'MTV Classic CA (720p)', 'HD'),
    ('xite-hits',          'زایت هیتس',        'XITE Hits',         'music', 'music', 'XITE Hits (1080p)', 'HD'),
    ('xite-rock',          'زایت راک',         'XITE Rock x Metal', 'music', 'music', 'XITE Rock x Metal (1080p)', 'HD'),
    ('now-80s',            'ناو ۸۰s',          'Now 80s',           'music', 'music', 'Now 80s (1080p)', 'HD'),
    ('now-90s00s',         'ناو ۹۰ و ۰۰',      'Now 90s00s',        'music', 'music', 'Now 90s00s (1080p)', 'HD'),
    ('trace-urban',        'تریس اربن',        'Trace Urban',       'music', 'music', 'Trace Urban (1080p)', 'HD'),
    ('deluxe-music',       'دلوکس موزیک',      'Deluxe Music',      'music', 'music', 'Deluxe Music (720p)', 'HD'),
    ('deluxe-dance',       'دلوکس دنس',        'Deluxe Dance',      'music', 'music', 'Deluxe Dance (1080p)', 'HD'),
    ('deluxe-rap',         'دلوکس رپ',         'Deluxe Rap',        'music', 'music', 'Deluxe Rap (1080p)', 'HD'),
    ('kiss-kiss-tv',       'کیس کیس تی‌وی',    'Kiss Kiss TV',      'music', 'music', 'Kiss Kiss TV (1080p)', 'HD'),
    ('stingray-djazz',     'استینگری جاز',     'Stingray DJAZZ',    'music', 'music', 'Stingray DJAZZ (1080p)', 'HD'),
    ('stingray-classic-rock','استینگری کلاسیک راک','Stingray Classic Rock','music','music','Stingray Classic Rock (1080p)','HD'),

    # ---------------- ورزشی ----------------
    ('varzesh-tv',         'شبکه ورزش',        'Varzesh TV',        'sports', 'sports', 'Varzesh TV', 'HD'),
    ('bein-xtra',          'بی‌این اسپورتس',   'beIN SPORTS XTRA',  'sports', 'sports', 'beIN SPORTS XTRA (1080p)', 'HD'),
    ('fifa-plus',          'فیفا پلاس',        'FIFA+',             'sports', 'sports', 'FIFA+ (720p)', 'HD'),
    ('fifa-plus-women',    'فیفا پلاس زنان',   'FIFA+ Women',       'sports', 'sports', 'FIFA+ Women (720p)', 'HD'),
    ('red-bull-tv',        'رد بُل تی‌وی',     'Red Bull TV',       'sports', 'sports', 'Red Bull TV (1080p)', 'HD'),
    ('dazn-combat',        'دازن کامبت',       'DAZN Combat',       'sports', 'sports', 'DAZN Combat (684p)', 'SD'),
    ('dazn-darts',         'دازن دارتس',       'DAZN Darts',        'sports', 'sports', 'DAZN Darts x Pluto TV', 'SD'),
    ('fight-network',      'فایت نتورک',       'Fight Network',     'sports', 'sports', 'Fight Network (1080p)', 'HD'),
    ('fightbox',           'فایت‌باکس',        'FightBox',          'sports', 'sports', 'FightBox', 'HD'),
    ('premier-sports',     'پریمیر اسپورتس',   'Premier Sports',    'sports', 'sports', 'Premier Sports (1080p)', 'HD'),
    ('tennis-channel',     'تنیس چنل',         'Tennis Channel',    'sports', 'sports', 'Tennis Channel (1080p)', 'HD'),
    ('tennis-channel-2',   'تنیس چنل ۲',       'Tennis Channel +2', 'sports', 'sports', 'Tennis Channel +2 (720p)', 'HD'),
    ('golf-channel',       'گلف چنل',          'Golf Channel',      'sports', 'sports', 'Golf Channel', 'HD'),
    ('olympic-channel',    'المپیک چنل',       'Olympic Channel',   'sports', 'sports', 'Olympic Channel (1080p) [Geo-blocked]', 'HD'),
    ('nfl-channel',        'ان‌اف‌ال',         'NFL Channel',       'sports', 'sports', 'NFL Channel (720p)', 'HD'),
    ('nbc-sports-now',     'ان‌بی‌سی اسپورتس', 'NBC Sports NOW',    'sports', 'persian', 'NBC Sports NOW', 'HD'),
    ('fubo-sports',        'فوبو اسپورتس',     'Fubo Sports Network','sports','sports', 'Fubo Sports Network (1080p)', 'HD'),
    ('tsn-the-ocho',       'تی‌اس‌ان اوچو',    'TSN The Ocho',      'sports', 'sports', 'TSN The Ocho (1080p)', 'HD'),
    ('espn8-the-ocho',     'ای‌اس‌پی‌ان اوچو', 'ESPN8: The Ocho',   'sports', 'sports', 'ESPN8: The Ocho (1080p)', 'HD'),
    ('mutv',               'مان‌یونایتد تی‌وی', 'MUTV',              'sports', 'sports', 'MUTV (720p)', 'HD'),
    ('mlb-channel',        'ام‌ال‌بی',         'MLB Channel',       'sports', 'persian', 'MLB Channel', 'HD'),
    ('trace-sport-stars',  'تریس اسپورت',      'Trace Sport Stars', 'sports', 'sports', 'Trace Sport Stars (1080p)', 'HD'),
    ('cbc-sport',          'سی‌بی‌سی اسپرت',   'CBC Sport',         'sports', 'sports', 'CBC Sport [Geo-blocked]', 'HD'),
    ('adjarasport-1',      'آجاراسپورت',       'Adjarasport 1',     'sports', 'sports', 'Adjarasport 1', 'HD'),
]

CATEGORIES = [
    {'id': 'persiana', 'title': 'پرشیانا گروپ', 'subtitle': 'کانال‌های گروه پرشیانا', 'emoji': '📺', 'color': '#7C4DFF'},
    {'id': 'news',     'title': 'خبری',         'subtitle': 'شبکه‌های خبری ایران و جهان', 'emoji': '📰', 'color': '#00B0FF'},
    {'id': 'music',    'title': 'موزیک',        'subtitle': 'کانال‌های موسیقی و کلیپ', 'emoji': '🎵', 'color': '#FF4081'},
    {'id': 'sports',   'title': 'ورزشی',        'subtitle': 'کانال‌های ورزشی و مسابقات زنده', 'emoji': '⚽', 'color': '#00E676'},
]

def resolve(cat_id, src, key):
    if isinstance(key, dict):
        return key['url'], key.get('logo', ''), ''
    table = SRC[src]
    if key not in table:
        sys.exit('MISSING in %s: %r' % (src, key))
    e = table[key]
    return e['url'].strip(), (e.get('logo') or '').strip(), e.get('group') or ''

channels, missing_logo = [], []
for cid, fa, en, cat, src, key, quality in TABLE:
    url, logo, group = resolve(cat, src, key)
    if not logo:
        missing_logo.append(cid)
    channels.append({
        'id': cid, 'name': fa, 'nameEn': en, 'category': cat,
        'logo': logo, 'url': url, 'quality': quality,
    })

doc = {
    'version': 2,
    'updated': datetime.date.today().isoformat(),
    'note': 'Channel list curated from iptv-org/iptv (categories) and Samhouston010/persian-tv playlists.',
    'sources': [
        'https://github.com/iptv-org/iptv',
        'https://github.com/Samhouston010/persian-tv',
    ],
    'categories': CATEGORIES,
    'channels': channels,
}

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'src', 'main', 'assets', 'channels.json')
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write('\n')

from collections import Counter
print('wrote', out)
print('counts:', Counter(c['category'] for c in channels))
print('total:', len(channels), '| channels without logo:', missing_logo)
