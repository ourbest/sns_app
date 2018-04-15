import re
import sys
from datetime import datetime


def do_find(file):
    with open(file, 'r') as lines:
        for line in lines:
            p = re.findall('\[(.+) \+0800\].+ (\d+) "http:\/\/.+\.cutt\.com" "(\d+ [\d\.]+ \(.+\))" "', line)
            if p:
                (dt, uid, ua) = p[0]
                t = datetime.strptime(dt, '%d/%b/%Y:%H:%M:%S')
                print('insert ignore into partner_DeviceUserAgent '
                      '(ua, userId, updateTime) values (\'%s\', %s, \'%s\');' % (
                          ua.replace('\'', '\'\''), uid, t.strftime('%Y-%m-%d %H:%M:%S')))


if __name__ == '__main__':
    do_find(sys.argv[1])
