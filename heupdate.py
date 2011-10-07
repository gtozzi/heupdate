#!/usr/bin/env python

# Hurricane Electric IPv6 Tunnel Auto-Update script
# Author Gabriele Tozzi <gabriele@tozzi.eu>
# License: GPL

import os, sys
import logging
from optparse import OptionParser
import ConfigParser
import re, string
import subprocess
import urlparse, httplib

class main:
    NAME = 'HE Updater'
    VERSION = '0.1'

    def run(self):
        ''' Main entry point '''

        # Configure console logging
        logging.basicConfig(
            level = logging.INFO,
            format = '%(name)-12s: %(levelname)-8s %(message)s',
            datefmt = '%Y-%m-%d %H:%M:%S',
        )

        # Create logger
        self.__log = logging.getLogger('heupdater')

        # Read command line
        usage = "%prog [options] <config_file>"
        parser = OptionParser(usage=usage, version=self.NAME + ' ' + self.VERSION)
        parser.add_option("-q", "--quiet", dest="quiet",
            help="Suppress non warning output (overrides -v)", action="store_true")
        parser.add_option("-v", "--verbose", dest="verbose",
            help="Be verbose", action="store_true")

        (options, args) = parser.parse_args()

        if len(args) != 1:
            parser.error("unvalid number of arguments")

        # Change debug level if needed
        if options.quiet:
            self.__log.setLevel(logging.WARNING)
        elif options.verbose:
            self.__log.setLevel(logging.DEBUG)

        # Read config file
        self.__config = ConfigParser.ConfigParser()
        self.__config.read(args[0])

        # Determine my ip
        method = self.__config.get('main', 'method')
        if method == 'ifconfig':
            self.__ip = self.__getIpIfconfig()
        else:
            self.__log.critical('Unknown method: ' + str(method))
        self.__log.info('Current IP address: ' + self.__ip)

        # Get last announced IP from spool
        lastip = self.__getSpoolIp()
        self.__log.info('Last IP announced: ' + lastip)

        # Proceed?
        if self.__ip == lastip:
            self.__log.info('IP is updated. Nothing to do.')
            sys.exit(0)

        # Update IP on server
        self.__updateEndPoint()

    def __getIpIfconfig(self):
        ''' Gets current IP from ifconfig and returns it '''

        ifconfig = str(self.__config.get('ifconfig', 'bin'))
        interface = str(self.__config.get('ifconfig', 'interface'))
        pat = re.compile(self.__config.get('ifconfig', 'filter'), re.M)

        cmd = ( ifconfig, interface )
        self.__log.debug('Running ifconfig: ' + ' '.join(cmd))
        out = subprocess.check_output(cmd)
        self.__log.debug("Command output: \n" + out)
        self.__log.debug('Searching for pattern: ' + pat.pattern)
        m = pat.search(out)
        if not m or not len(m.groups()):
            raise RuntimeError('Unable to get current IP from ifconfig')
        return m.group(1)

    def __getSpoolIp(self):
        ''' Gets last IP announced from spool file '''

        spoolfile = str(self.__config.get('main', 'spool'))
        try:
            f = open(spoolfile, 'rt')
        except IOError as e:
            if e.errno == 2:
                # No such file or directory, try to create it
                f = open(spoolfile, 'wt')
                return None
            else:
                raise e
        ip = f.readline().strip()
        f.close()
        return ip
    
    def __updateEndPoint(self):
        ''' Updates current IPv4 endpoint from self.__ip '''

        url = string.Template(self.__config.get('server', 'url'))
        user = str(self.__config.get('server', 'user'))
        pwd = str(self.__config.get('server', 'pass'))
        tunnel = str(self.__config.get('server', 'tunnel_id'))
        url = url.substitute(ip=self.__ip, tunnelid=tunnel)
        url = urlparse.urlparse(url)

        self.__log.debug('Contacting ' + url.geturl())
        if url.scheme == 'http':
            server = httplib.HTTPConnection(url.netloc)
        elif url.scheme == 'https':
            server = httplib.HTTPSConnection(url.netloc)
        else:
            raise NotImplementedError('Unknown server URL scheme ' + url.scheme)
        server.request('GET', url.path+'?'+url.query)

        res = server.getresponse()
        self.__log.debug("Got Response:\n" + unicode(res))

        server.close()

if __name__ == '__main__':
    app = main()
    ret = app.run()
    sys.exit(ret)

