#!/usr/bin/python

#
# Copyright (C) 2015, Jaguar Land Rover
#
# This program is licensed under the terms and conditions of the
# Mozilla Public License, version 2.0.  T full text of the 
# Mozilla Public License is at https://www.mozilla.org/MPL/2.0/
#
#  Create a certificate giving the sender the right to invoke and 
#

import getopt
import sys
from Crypto.PublicKey import RSA 

# apt-get install python-dev
# apt-get install libffi-dev
# pip install cryptography
# pip install PyJWT

import jwt
import time
import json
import base64

def usage():
    print "Usage:", sys.argv[0], "--id=<id> --invoke='<services>' -register='<services>' \\"
    print "                       --root_key=<file> --start='<date/time>' --stop='<date/time>' \\"
    print "                       --out=<file>"
    print
    print "  --id=<id>                       System-wide unique certificate ID"
    print 
    print "  --invoke='<services>'           Right to invoke service. Space separate multiple services."
    print 
    print "  --register='<services>'         Right to register service. Space separate multiple services."
    print "                                  At least one --invoke or --register must be given."
    print 
    print "  --root_key=<file>               Private root key to sign certificate with"
    print "                                  Mandatory"
    print
    print "  --device_key=<file>             Public device key to include in certificate"
    print "                                  Mandatory"
    print
    print "  --start='<YYYY-MM-DD HH:MM:SS>' Date and time when certificate is activated."
    print "                                  Default: current time."
    print
    print "  --stop='<YYYY-MM-DD HH:MM:SS>'  Date and time when certificate is deactivated."
    print "                                  Default: 365 days from current time"
    print
    print "  --jwt_out=<file>                File name to store JWT-encoded certificate in."
    print "                                  Default: stdout"
    print
    print "  --cert_out=<file>               File name to unencoded JSON certificate in."
    print "                                  Default: Do not store certificate"
    print
    print "  --issuer=issuer                 Name of the issuer. Default: jaguarlandrover.com"
    print
    print "Root key file is generated by rvi_create_root_key.sh"
    print
    print "Device key is the '_pub.pem'-suffixed file created by rvi_create_device_key.py"
    print
    print "Certificate file specified by out should be placed in 'priv/certs'"
    print 
    print
    print "Example:"
    print "./rvi_create_certificate.py --id=317624d8-2ccf-11e5-993c-7f3b5182c649 \\"
    print "                            --device_key=device_key_pub.pem \\"
    print "                            --start='2015-12-01 00:00:00' \\"
    print "                            --stop='2015-12-31 23:59:59' \\"
    print "                            --root_key=root_key_priv.pem \\"
    print "                            --register='jlr.com/vin/abc/unlock jlr.com/vin/abc/lock' \\"
    print "                            --invoke='jlr.com/backend/report jlr.com/backend/set_state' \\"
    print "                            --jwt_out=lock_cert.jwt --cert_out=lock_cert.json"
    sys.exit(255)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", [ 'issuer=', 'invoke=', 'register=', 
                                                   'root_key=', 'start=', 
                                                   'stop=', 'cert_out=', 'id=',
                                                   'jwt_out=', 'device_key='])
except getopt.GetoptError as e:
    print
    print e
    print
    usage()

start=int(time.time())
stop=int(time.time()) + 86400 * 365

issuer='jaguarlandrover.com'
invoke=None
register=None
root_key=None
device_key=None
jwt_out_file=None
cert_out_file=None
id_string=None
for o, a in opts:
    if o == "--start":
        try:
            start = int(time.mktime(time.strptime(a, "%Y-%m-%d %H:%M:%S")))
        except:
            print
            print "Incorrect start time: {}".format(a)
            print
            usage()
            
    elif o == '--root_key':
        try:
            root_key_fname = a
            root_key_file = open(root_key_fname, "r")
            root_key = RSA.importKey(root_key_file.read())
            root_key_file.close()
        except IOError as e:
            print "Coould read root cert from {0}: {1}".format(a, e.strerror)
            sys.exit(255)

    elif o == '--device_key':
        try:
            device_key_file = open(a, "r")
            device_key = RSA.importKey(device_key_file.read())
            device_key_file.close()
        except IOError as e:
            print "Coould read root cert from {0}: {1}".format(a, e.strerror)
            sys.exit(255)

    elif o == "--stop":
        try:
            stop = int(time.mktime(time.strptime(a, "%Y-%m-%d %H:%M:%S")))
        except:
            print
            print "Incorrect stop time: {}".format(a)
            print
            usage()

    elif o == '--invoke':
        invoke=a.split(' ')

    elif o == '--register':
        register=a.split(' ')

    elif o == '--id':
        id_string=a

    elif o == '--issuer':
        issuer=a

    elif o == '--jwt_out':
        try:
            jwt_out_file = open(a, "w")
        except IOError as e:
            print "Coould write to JWT file {0}: {1}".format(a, e.strerror)
            sys.exit(255)

    elif o == '--cert_out':
        try:
            cert_out_file = open(a, "w")
        except IOError as e:
            print "Coould write to certificate file {0}: {1}".format(a, e.strerror)
            sys.exit(255)

    else:
        print
        print "Unknown command line argument: {}".format(o)
        print
        usage()
        
if jwt_out_file == None:
    jwt_out_file = sys.stdout

if not invoke and not register:
    print
    print "At least one --invoke or --register service must be specified."
    print
    usage()

if not root_key:
    print
    print "No --root_key=<root_key_file.pem> specified"
    print
    usage()

if not device_key:
    print
    print "No --device_key=<device_public_key_file.pem> specified"
    print
    usage()

if not id_string:
    print
    print "No --id=<id_string> specified"
    print
    usage()


# Create a JSON Web Key based off our public device key PEM file


cert = { 
    'iss': issuer,
    'id': id_string,
    'sources': register,
    'destinations': invoke,
    'create_timestamp': int(time.time()),
    'keys': [{
	"kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "e": base64.urlsafe_b64encode(str(device_key.e)),
        "n": base64.urlsafe_b64encode(str(device_key.n))
    }],
    'validity': { 
        'start': start,
        'stop': stop
    }
}


encoded = jwt.encode(cert, root_key.exportKey("PEM"), algorithm='RS256')

# Validate
try:
    jwt.decode(encoded, root_key.publickey().exportKey("PEM"), algorithm='RS256')
except:
    print "FAILED: Could not verify signed JSON Web Token using public part of"
    print "        root key {}".format(root_key_fname)


jwt_out_file.write(encoded)
jwt_out_file.close()

if cert_out_file:
    cert_out_file.write(json.dumps(cert, sort_keys=True, indent=4, separators=(',', ': ')) + '\n')
    cert_out_file.close()

