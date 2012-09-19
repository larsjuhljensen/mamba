import sys
import pg
import socket
import httplib

import mamba.util
import mamba.task
import mamba.http
import mamba.setup

def utf8str(text):
    return mamba.util.string_to_bytes(text, 'utf-8')
    
def str2sql(text):
    return pg.escape_string(utf8str(text))

class EditRequest(mamba.task.Request):

    def __init__(self, http):
        mamba.task.Request.__init__(self, http)
        self.name        = None
        self.document_id = None
                
    def _get_text(self, parent_node, child_name):
        child = parent_node.getElementsByTagName(child_name)
        if len(child) == 1:
            child = child[0]
            return child.childNodes[0].nodeValue.strip()
        return None
    
    def _connect_to_changelog_db(self):
        if 'changelog_database' in self.worker.params:
            host, port, user, passwd, database = self.worker.params['changelog_database'].split(':')
            try:
                conn = pg.connect(dbname=database, host=host, port=int(port), user=user, passwd=passwd)
                return conn
            except pg.InternalError, e:
                self.err(str(e).strip())
                return None
        else:
            return None
        
    def _connect_to_dictionary_db(self):
        if "tagging_database" in self.worker.params:
            host, port, user, passwd, database = self.worker.params['tagging_database'].split(':')
            try:
                conn = pg.connect(dbname=database, host=host, port=int(port), user=user, passwd=passwd)
                return conn
            except pg.InternalError, e:
                self.err(str(e).strip())
                return None
        else:
            return None
    
    def _select_serial_from_entities(self, conn):
        sql = "SELECT serial FROM entities WHERE type=%i AND identifier='%s';" % (self.entity_type, str2sql(self.entity_identifier))
        self.debug(sql)
        query  = conn.query(sql)
        result = query.getresult()
        if len(result) > 1:
            raise mamba.task.SyntaxError, 'Found more than one rows in "entities" for type: %i identifier: %s' % (self.entity_type, str2sql(self.entity_identifier))
        elif len(result) == 1:
            return result[0][0]
        else:
            return None
    
    def _select_names_from_dictionary(self, conn, serial):
        sql = "SELECT name FROM names WHERE serial=%i;" % (serial)
        self.debug(sql)
        query  = conn.query(sql)
        result = query.getresult()
        names = []
        for items in result:
            name = items[0]
            names.append(name)
        return names
    
    def _insert_name_into_dictionary(self, conn, serial):
        sql = str("INSERT INTO names (serial, name) VALUES (%i, '%s')" % (serial, str2sql(self.name)))
        self.debug(sql)
        try:
            result = conn.query(sql)
            self.debug(result)
            if result == None:
                return 200, 'Insert of name ' + self.name + ' succeded.'
            else:
                return 500, 'AddName failed to insert name: %s into the dictionary' % str2sql(self.name)
        except Exception, e:
            return 500, 'AddName failed:\nError during query processing.\nFailed with ' + str(type(e)) + ' message: ' + str(e)
            
    def _select_blocked_from_global(self, conn):
        sql = "SELECT blocked FROM global WHERE name='%s';" % str2sql(self.name)
        self.debug(sql)
        query  = conn.query(sql)
        result = query.getresult()
        if len(result) == 0:
            return None
        if len(result) == 1:
            blocked = result[0][0]
            return blocked
        else:
            raise RuntimeError, 'Found more than one row in table: global with name: '+self.name
            
    def _select_blocked_from_local(self, conn):
        sql = "SELECT blocked FROM local WHERE name='%s' AND document_id='%s';" % (str2sql(self.name), str2sql(self.document_id))
        self.debug(sql)
        query  = conn.query(sql)
        result = query.getresult()
        if len(result) == 0:
            return False
        if len(result) == 1:
            blocked = result[0][0]
            return blocked == 't'
        else:
            raise RuntimeError, 'Found more than one row in table: local with name: %s document_id: %s' % (str2sql(self.name), str2sql(self.document_id))
            
    def _select_all_from_global(self, conn):
        sql    = "SELECT * FROM global WHERE name = '%s'" % str2sql(self.name)
        self.debug(sql)
        query  = conn.query(sql)
        result = query.dictresult()
        return result
    
    def _insert_name_into_local(self, conn, blocked):
        # -----------------------------------------------------------
        # This function should be used as the general method for
        # black/white listings (block/allow name).
        # It does the proper checking of whether an actual new
        # row has to be inserted or, if it exists, should be updated.
        # -----------------------------------------------------------
        #
        # First check if there is a pre-existing row
        # in the local table for this name + document.
        #
        if not blocked:
            str_blocked = 'f'
            str_action  = 'white'
        else:
            str_blocked = 't'
            str_action  = 'black'
        sql = "SELECT blocked FROM local WHERE name='%s' AND document_id='%s';" % (str2sql(self.name), str2sql(self.document_id))
        self.info(sql)
        query  = conn.query(sql)
        result = query.getresult()
        self.info('Query returned', result)
        if len(result) == 0:
            sql = str("INSERT INTO local (name, document_id, blocked) VALUES ('%s', '%s', '%s')" % (str2sql(self.name), str2sql(self.document_id), str_blocked))
        else:
            sql = str("UPDATE ONLY local SET blocked='%s' WHERE name='%s' and document_id='%s'" % (str2sql(str_blocked), str2sql(self.name), str2sql(self.document_id)))
        try:
            self.info(sql)
            result = conn.query(sql)
            self.info('SQL insert in table=local returned', result)
            if result == None:
                page =  '<html>\n'
                page += '<head>\n'
                page += '  <title>Editing name "%s" on %s</title>\n' % (utf8str(self.name), utf8str(self.document_id))
                page += '</head>\n'
                page += '<body>\n'
                page += '  <p>The name <b>%s</b> was specifically %s-listed on:\n' % (utf8str(self.name), str_action)
                page += '  <table>\n'
                page += '   <tr>\n'
                page += '     <td><pre>    </pre></td>\n'
                page += '     <td><a href="%s">%s</a></td>\n' % (utf8str(self.document_id), utf8str(self.document_id))
                page += '   </tr>\n'
                page += '  </table>\n'
                page += '  </p>\n'
                page += '  <p>Thank you for using the <a href="http://reflect.ws">Reflect</a> service.</p>\n'
                page += '</body>\n'
                page += '</html>\n'
                return 200, page
            else:
                return 409, 'Conflict. Name: "%s" could not be locally %s-listed.' % (utf8str(self.name), str_action)
        except Exception, e:
            return 500, 'Failure. Original error: ' + str(type(e)) + ' message: ' + str(e)

    def _update_tagger_and_changelog(self, action, name, document_id, type=None, identifier=None):
        conn = self._connect_to_changelog_db()
        if conn:
            xml = []
            xml.append('<soap:Body>')
            xml.append('<%s xmlns="Reflect">' % action)
            xml.append('<name xsi:type="xsd:string">%s</name>' % utf8str(name))
            if document_id:
                xml.append('<document_id xsi:type="xsd:string">%s</document_id>' % utf8str(document_id))
            if type:
                xml.append('<type xsi:type="xsd:int">%i</type>' % type)
            if identifier:
                xml.append('<identifier xsi:type="xsd:string">%s</identifier>' % utf8str(identifier))
            xml.append('</%s>' % action)
            xml.append('</soap:Body>')
            xml  = pg.escape_string(''.join(xml))
            ip   = pg.escape_string(self.http.remote_ip)
            uuid = pg.escape_string(self.http.uuid)
            sql  = str("INSERT INTO log (client_ip, uuid, time, xml) VALUES ('%s', '%s', CURRENT_TIMESTAMP, '%s')" % (ip, uuid, xml))
            self.debug(sql)
            try:
                result = conn.query(sql)
                self.debug('SQL insert in table=local returned', result)
                if result == None:
                    self.debug('Changelog update OK')
                else:
                    self.err("Error updating the change-log databse.")
            except Exception, e:
                self.err("Error updating the change-log databse for action: %s error message: '%s'" % (action, str(e)))
            
        if action.lower() == 'addname':
            mamba.setup.config().tagger.AddName(name, type, identifier)
            self.info('Updated C/C++ tagger with AddName of "%s", %i, %s' % (utf8str(name), type, utf8str(identifier)))
            
        elif action.lower() == 'blockname':
            mamba.setup.config().tagger.BlockName(name, document_id)
            self.info('Updated C/C++ tagger with BlockName of "%s" on document %s' % (utf8str(name), utf8str(document_id)))
            
        elif action.lower() == 'allowname':
            mamba.setup.config().tagger.AllowName(name, document_id)
            self.info('Updated C/C++ tagger with AllowName of "%s" on document %s' % (utf8str(name), utf8str(document_id)))
                    
    def main(self):
        self.parse()
        self.queue('edit')
    


class AddName(EditRequest):
    
    def parse(self):
        rest = mamba.task.RestDecoder(self)
        
        for check in ('name', 'document_id', 'entity_type', 'entity_identifier'):
            if rest[check] == None:
                raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
            
        self.name              = rest['name']
        self.document_id       = rest['document_id']
        self.entity_type       = int(rest['entity_type'])
        self.entity_identifier = rest['entity_identifier']
            
    def edit(self):
        reply = mamba.http.HTTPResponse(self, "AddName succeeded. Name/type/ID: '%s'/%s/%s" % (utf8str(self.name), self.entity_type, utf8str(self.entity_identifier)))
        conn  = self._connect_to_dictionary_db()
        if conn == None:
            reply.status = 503
            reply.body   = "Database connection failed"
            reply.send()
            return            
        # --------------------------------------------------------
        # IF name NOT IN dictonary THEN
        #    insert name into dictonary
        # ELSE:
        #    IF name IN local_black_list THEN:
        #       remove name from local_black_list (remove or not?)
        #       insert name into local_white_list
        #    ELSE IF name in global_stop_list:
        #       insert name into local-white-list
        # --------------------------------------------------------
        # 
        # Do Serial exists for Type + Identifier?
        # 
        serial = self._select_serial_from_entities(conn)
        if serial:
            # 
            # Yes.
            # Do Name + Serial exists?
            # 
            name_exists = False
            for xname in self._select_names_from_dictionary(conn, serial):
                #self.debug('name:',name, 'xname:', xname)
                if xname == self.name:
                    name_exists = True
                    break
            if name_exists:
                # 
                # Yes.
                # Is the Name blocked locally or globally?
                # 
                blocked_locally  = self._select_blocked_from_local(conn)
                blocked_globally = self._select_blocked_from_global(conn)
                if blocked_globally or blocked_locally:
                    # 
                    # Yes, name is blocked.
                    # Locally blocked?
                    # 
                    status, msg = self._insert_name_into_local(conn, blocked=False)
                    reply.status = status
                    reply.body = msg
                    if status == 200:
                        #
                        # Remember to tell tagger(s) that the name was white-listed locally.
                        #
                        self._update_tagger_and_changelog('AllowName', self.name, self.document_id)
            else:
                #
                # The name does not exitst in the dictionary for
                # the given Type + Identifier.
                # We insert the name in the names table.
                # 
                status, msg = self._insert_name_into_dictionary(conn, serial)
                reply.status = status
                reply.body = msg
                if status == 200: # Insert was made.
                    #
                    # Since the name was successfully inserted we
                    # must inform the tagger about the change to
                    # the state of the database (a new name was added).
                    # Update the tagger with information that a
                    # new name has been added to the dictionary!
                    #
                    self._update_tagger_and_changelog('AddName', self.name, self.document_id, self.entity_type, self.entity_identifier)
            #
            # Store organism (entity type) associated with the document.
            #
            if self.entity_type > 0 and self.document_id != None:
                sql = "SELECT COUNT(*) FROM document_types where document_identifier='%s' and type=%i" % (str2sql(self.document_id), self.entity_type)
                query = conn.query(sql)
                result = query.getresult()
                if result[0][0] == 0:
                    #
                    # The entity-type is not registred explicitely for this page.
                    # The user is trying to add a name for a specific organism/type
                    # thus we will register this type for the page to ensure the
                    # complete and correct tagging of this page in the future.
                    #
                    sql = "INSERT INTO document_types (document_identifier, type) VALUES ('%s', %i)" % (str2sql(self.document_id), self.entity_type)
                    result = conn.query(sql)
                    if result != None:
                        reply = mamba.http.HTTPErrorResponse(self, 500, 'Database error. Could not register the entity-type for this document.')
                        reply.send()
                        return
                    self.debug('User registred entity-type %i for document_id %s.' % (self.entity_type, str2sql(self.document_id)))
            
        else:
            errmsg = str('AddName failed to find a serial for entity_type %i and identifier "%s".' % (self.entity_type, str2sql(self.entity_identifier)))
            reply.status = 500
            reply.body = errmsg
        conn.close()
        self.debug('Closed database connection')
        self.debug('AddName - reply:', reply)
        reply.send()
        
        
class AllowName(EditRequest):
    
    def parse(self):
        rest = mamba.task.RestDecoder(self)
        for check in ('name', 'document_id'):
            if rest[check] == None:
                raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
        self.name        = rest['name']
        self.document_id = rest['document_id']
    
    def edit(self):
        reply = mamba.http.HTTPResponse(self, 'AllowName succeeded. Name: "%s"' % utf8str(self.name))
        conn  = self._connect_to_dictionary_db()
        if conn == None:
            reply.status = 503
            reply.body = "Database connection failed"
        else:
            status, msg = self._insert_name_into_local(conn, blocked = False)
            conn.close()
            reply.status = status
            reply.body = msg
            self._update_tagger_and_changelog('AllowName', self.name, self.document_id)
        reply.send()
    

class BlockName(EditRequest):
    
    def parse(self):
        rest = mamba.task.RestDecoder(self)
        for check in ('name', 'document_id'):
            if rest[check] == None:
                raise mamba.task.SyntaxError, 'Required parameter "%s" missing.' % check
        self.name = rest['name']
        self.document_id = rest['document_id']

    def edit(self):
        reply = mamba.http.HTTPResponse(self, 'BlockName succeeded. Name: "%s"' % utf8str(self.name))
        conn  = self._connect_to_dictionary_db()
        if conn == None:
            reply = mamba.http.HTTPErrorResponse(self, 503, 'Database connection failed')
        else:
            #
            # Put Name + Doc.ID in table; local.
            #
            status, msg = self._insert_name_into_local(conn, blocked = True)
            if status == 200:
                reply = mamba.http.HTTPResponse(self, msg, content_type='text/html')
                #
                # Success.
                # Local was updated so the name is now blocked on the page.
                # But is the name blocked on at least 5 other pages?
                # If so we must globally block the name also.
                sql    = "SELECT COUNT(*) FROM local WHERE name = '%s' AND blocked='t'" % str2sql(self.name)
                self.info(sql)
                query  = conn.query(sql)
                result = query.getresult()
                if result[0][0] >= 5:
                    #
                    # Yes, name is locally blacklisted at least 5 times.
                    # Ok, then we must elevate the name to be globally blocked.
                    # We first check whether the name is already in global.
                    #
                    # However - and this is quite important - if the name is
                    # already just in the global list then don't change the status
                    # of that name in the global list. Why? Because it may be
                    # defined initially as a globally white-listed name or it may
                    # have already been globally black-listed in which case it is
                    # irrellevant to globally black-list it again due to a 5strike.
                    #
                    result = self._select_all_from_global(conn)
                    #
                    # Only globally black-list name if it is not mentioned
                    # on the global list already.
                    #
                    if len(result) == 0:
                        #
                        # Yes, the name was in the global list.
                        # Update the 'source = 5strike' and 'blocked' columns.
                        #
                        sql = str("INSERT INTO global (name, blocked, source) VALUES ('%s', '%s', '%s')" % (str2sql(self.name), 't', '5strike'))
                        self.info(sql)
                        try:
                            result = conn.query(sql)
                            self.info(result)
                            if result == None:
                                self.debug('Blockname: Name "%s" was globally blocked (5strike).' % utf8str(self.name))
                        except Exception, e:
                            self.err('BlockName failure. Original error: ' + str(type(e)) + ' message: ' + str(e))
                    self.document_id = None # Signalling we are putting the name on global black-list.
                self._update_tagger_and_changelog('BlockName', self.name, self.document_id)
            else:
                reply = mamba.http.HTTPErrorResponse(self, status, msg)
        reply.send()
