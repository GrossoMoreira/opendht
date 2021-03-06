#!/usr/bin/env python3
# Copyright (c) 2016 Savoir-faire Linux Inc.
# Author: Adrien Béraud <adrien.beraud@savoirfairelinux.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; If not, see <http://www.gnu.org/licenses/>.

from twisted.web import server, resource
from twisted.internet import reactor, endpoints
from urllib.parse import urlparse

import opendht as dht
import base64, json

class DhtServer(resource.Resource):
    isLeaf = True
    node = dht.DhtRunner()

    def __init__(self, port, bootstrap):
        self.node.run(port=port)
        b_url = urlparse('//'+bootstrap)
        self.node.bootstrap(b_url.hostname, str(b_url.port) if b_url.port else '4222')

    def render_GET(self, req):
        uri = req.uri[1:]
        h = dht.InfoHash(uri) if len(uri) == 40 else dht.InfoHash.get(uri.decode())
        print('GET', '"'+uri.decode()+'"', h)
        res = self.node.get(h)
        req.setHeader(b"content-type", b"application/json")
        return json.dumps({'{:x}'.format(v.id):{'base64':base64.b64encode(v.data).decode()} for v in res}).encode()

    def render_POST(self, req):
        uri = req.uri[1:]
        data = req.args[b'data'][0] if b'data' in req.args else None
        if not data and b'base64' in req.args:
            data = base64.b64decode(req.args[b'base64'][0])
        h = dht.InfoHash(uri) if len(uri) == 40 else dht.InfoHash.get(uri.decode())
        print('POST', h, data)
        req.setHeader(b"content-type", b"application/json")
        if data:
            self.node.put(h, dht.Value(data))
            return json.dumps({'success':True}).encode()
        else:
            req.setResponseCode(400)
            return json.dumps({'success':False, 'error':'no data parameter'}).encode()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Launch an OpenDHT node with an HTTP control interface')
    parser.add_argument('-p', '--port', help='OpenDHT port to bind', type=int, default=4222)
    parser.add_argument('-hp', '--http-port', help='HTTP port to bind', type=int, default=8080)
    parser.add_argument('-b', '--bootstrap', help='bootstrap address', default="bootstrap.ring.cx:4222")
    args = parser.parse_args()
    endpoints.serverFromString(reactor, "tcp:"+str(args.http_port)).listen(server.Site(DhtServer(args.port, args.bootstrap)))
    reactor.run()
