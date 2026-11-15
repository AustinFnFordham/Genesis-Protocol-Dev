"""Non-persisting Git helper. Never invoke manually to display a credential."""
import os
import sys


def main():
    if len(sys.argv) != 2 or sys.argv[1] != 'get':
        return
    values = dict(line.rstrip('\n').split('=',1) for line in sys.stdin if '=' in line)
    if (values.get('protocol') == 'https' and values.get('host') == 'github.com'
            and values.get('path','').removesuffix('.git') == 'AustinFnFordham/Genesis-Protocol-Dev'):
        token = os.environ.get('GENESIS_GITHUB_TOKEN')
        if token and '\n' not in token and '\r' not in token:
            sys.stdout.write('username=x-access-token\npassword=' + token + '\n\n')


if __name__ == '__main__':
    main()
