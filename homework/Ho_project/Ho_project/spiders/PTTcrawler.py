# -*- coding: utf-8 -*-
import scrapy
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pprint import pprint

# ����Ŀ�˾Wַ: https://www.ptt.cc/bbs/Gossiping/M.1557928779.A.0C1.html
class PttcrawlerSpider(scrapy.Spider):
    name = 'PTTCrawler'
    allowed_domains = ['www.ptt.cc']
    start_urls = ['https://www.ptt.cc/bbs/Gossiping/M.1557928779.A.0C1.html']
    cookies = {'over18': '1'}

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse, cookies=self.cookies)

    def parse(self, response):
        # ���O�W퓻ؑ����� 200 OK ��Ԓ, �҂�ҕ�����Ո��ʧ��
        if response.status != 200:
            print('Error - {} is not available to access'.format(response.url))
            return

        # ���W퓻ؑ��� HTML ���� BeautifulSoup ������, �����҂������˻` (tag) �YӍȥ�^�V����
        soup = BeautifulSoup(response.text)

        
        # ȡ�����������w
        main_content = soup.find(id='main-content')
        
        # ���������Ќ����Y�� (meta), �҂��ڏČ��Եą^�K���������� (author), �����} (title), �l������ (date)
        metas = main_content.select('div.article-metaline')
        author = ''
        title = ''
        date = ''
        if metas:
            if metas[0].select('span.article-meta-value')[0]:
                author = metas[0].select('span.article-meta-value')[0].string
            if metas[1].select('span.article-meta-value')[0]:
                title = metas[1].select('span.article-meta-value')[0].string
            if metas[2].select('span.article-meta-value')[0]:
                date = metas[2].select('span.article-meta-value')[0].string

            # �� main_content ���Ƴ� meta �YӍ��author, title, date �c���������YӍ��
            #
            # .extract() �������ԅ����ٷ��ļ�
            #  - https://www.crummy.com/software/BeautifulSoup/bs4/doc/#extract
            for m in metas:
                m.extract()
            for m in main_content.select('div.article-metaline-right'):
                m.extract()
        
        # ȡ�����ԅ^���w
        pushes = main_content.find_all('div', class_='push')
        for p in pushes:
            p.extract()
        
        # �����������а������� �l��վ: �����ߌ��I��(ptt.cc), ����: xxx.xxx.xxx.xxx���Ę�ʽ
        # ͸�^ regular expression ȡ�� IP
        # ����ִ��а��������̖������, �@߅���hʹ�� unicode ����ʽ u'...'
        try:
            ip = main_content.find(text=re.compile(u'�� �l��վ:'))
            ip = re.search('[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*', ip).group()
        except Exception as e:
            ip = ''
        
        # �Ƴ��������w�� '�� �l��վ:', '�� From:', ���м����N�հ� (�� = u'\u203b', �� = u'\u25c6')
        # ����Ӣ����, ���ļ����Ę��c, �Wַ, ���������̖
        #
        # ͸�^ .stripped_strings �ķ�ʽ���Կ����Ƴ����N�հׁKȡ������, �Ʌ����ٷ��ļ� 
        #  - https://www.crummy.com/software/BeautifulSoup/bs4/doc/#strings-and-stripped-strings
        filtered = []
        for v in main_content.stripped_strings:
            # �����ִ��_�^���������̖������ '--' �_�^��, �҂�������������
            if v[0] not in [u'��', u'��'] and v[:2] not in [u'--']:
                filtered.append(v)

        # ���xһЩ�����̖�cȫ�η�̖���^�V��
        expr = re.compile(u'[^һ-��������������������������\s\w:/-_.?~%()]')
        for i in range(len(filtered)):
            filtered[i] = re.sub(expr, '', filtered[i])
        
        # �Ƴ��հ��ִ�, �M���^�V������ּ������±��� (content)
        filtered = [i for i in filtered if i]
        content = ' '.join(filtered)
        
        # ̎�����ԅ^
        # p Ӌ�����Ĕ���
        # b Ӌ��u�Ĕ���
        # n Ӌ����^����
        p, b, n = 0, 0, 0
        messages = []
        for push in pushes:
            # �������Զ���]�� push-tag �����^
            if not push.find('span', 'push-tag'):
                continue
            
            # �^�V�~��հ��c�Q�з�̖
            # push_tag �Д�������, ���^߀�Ǉu��
            # push_userid �Д����Ե������l
            # push_content �Д����ԃ���
            # push_ipdatetime �Д��������ڕr�g
            push_tag = push.find('span', 'push-tag').string.strip(' \t\n\r')
            push_userid = push.find('span', 'push-userid').string.strip(' \t\n\r')
            push_content = push.find('span', 'push-content').strings
            push_content = ' '.join(push_content)[1:].strip(' \t\n\r')
            push_ipdatetime = push.find('span', 'push-ipdatetime').string.strip(' \t\n\r')

            # ���������Ե��YӍ, �K�yӋ�Ƈu�Ĕ���
            messages.append({
                'push_tag': push_tag,
                'push_userid': push_userid,
                'push_content': push_content,
                'push_ipdatetime': push_ipdatetime})
            if push_tag == u'��':
                p += 1
            elif push_tag == u'�u':
                b += 1
            else:
                n += 1
        
        # �yӋ�Ƈu��
        # count ���Ƈu����ֿ��@ƪ��������߀�Ǉu�ı��^��
        # all �鿂�����Ԕ��� 
        message_count = {'all': p+b+n, 'count': p-b, 'push': p, 'boo': b, 'neutral': n}
        
        # ���������YӍ
        data = {
            'url': response.url,
            'article_author': author,
            'article_title': title,
            'article_date': date,
            'article_content': content,
            'ip': ip,
            'message_count': message_count,
            'messages': messages
        }
        yield data
