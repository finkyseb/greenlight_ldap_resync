#!/usr/bin/env python3

import ldap
import sys
import psycopg2
import json

with open("conf/.conf.json") as conf_file:
    conf = json.load(conf_file)

ldap_server = f"ldap://{conf['ldap']['host']}:{conf['ldap']['port']}"
# print(ldap_server)

basedn = "ou=uds,ou=people,o=annuaire"
binddn = conf['ldap']['binddn']
pw = conf['ldap']['pw']

psql_data = f"host={conf['greenlightDB']['host']} dbname={conf['greenlightDB']['dbname']} " \
            f"user={conf['greenlightDB']['user']} password={conf['greenlightDB']['pw']}"

ldp = ldap.initialize(ldap_server)

searchFilter = "(&(udsActive=TRUE)(!(udsLocked=TRUE))(|(!(udsDataSource=MANUEL))(&(udsDataSource=MANUEL)" \
               "(udsAnonymousType=temporary)))(|(eduPersonPrimaryAffiliation=employee)" \
               "(eduPersonPrimaryAffiliation=faculty)(eduPersonPrimaryAffiliation=researcher)" \
               "(!(eduPersonPrimaryAffiliation=*))))"

""" Test mode """
 
searchFilter = "(uid=unfricht)"

searchAttribute = ["uid", "sn", "givenName", "cn"]
searchScope = ldap.SCOPE_SUBTREE
try:
    ldp.protocol_version = ldap.VERSION3
    ldp.simple_bind_s(binddn, pw)
except ldap.INVALID_CREDENTIALS:
    print("Your username or password is incorrect.")
    sys.exit(0)
except ldap.LDAPError as e:
    if type(e.message) == dict and 'desc' in e.message:
        print(e.message['desc'])
    else:
        print(e)
    sys.exit(0)
try:
    ldap_result_id = ldp.search(basedn, searchScope, searchFilter, searchAttribute)
    result_set = []
    while 1:
        result_type, result_data = ldp.result(ldap_result_id, 0)
        if not result_data:
            break
        else:
            if result_type == ldap.RES_SEARCH_ENTRY:
                result_set.append(result_data)
except ldap.LDAPError as e:
    print(e)
ldp.unbind_s()

# Communication with Postgres,
conn = None
try:
    conn = psycopg2.connect(psql_data)
    cur = conn.cursor()

    for j in range(len(result_set)):
        givenName = result_set[j][0][1]['givenName'][0].decode('utf-8')
        surName = result_set[j][0][1]['sn'][0].decode('utf-8')
        uid = result_set[j][0][1]['uid'][0].decode('utf-8')
        cn = result_set[j][0][1]['cn'][0].decode('utf-8')
        fullname = surName + " " + givenName

        print(f"UPDATE users SET name='{cn}' WHERE username='{uid}';")
        #cur.execute('UPDATE users SET name=%s WHERE username=%s', (fullname, uid))

    print("Committing to Database")
    #conn.commit()

except (Exception, psycopg2.DatabaseError) as error:
    print(error)
finally:
    if conn is not None:
        conn.close()
        print('Database connection closed.')
