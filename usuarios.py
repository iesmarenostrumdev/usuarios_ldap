#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from xml.dom import minidom
from xmlrpclib import *
import logging
import urllib2
import traceback
import ConfigParser
from Crypto.Cipher import AES
import base64
import rijndael
import math
import os
import time
from pathlib import Path

# Para correcta localización de los archivos de log, last_check, etc.
dir = os.path.dirname(os.path.abspath(__file__))

#Archivo para log
log_file = os.path.join(dir, 'usuarios.log')

# Archivo de lock. En directorio /tmp para que se borre en arranque de sistema en caso de que haya un cuelgue
# lock_file = os.path.join(dir, 'running')
lock_file = '/tmp/usuarios_running'

# Nombre de archivo que almacena fecha y hora del último chequeo
check_file = os.path.join(dir, 'last_check')

# Archivo de configuración
config_file = os.path.join(dir, 'usuarios.config')

# Logs
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=log_file,level=logging.DEBUG)

def excep(type, value, tb):
  logging.error("Excepción: {0} {1}.".format(str(value), traceback.format_tb(tb)))
  # Eliminamos archivo de lock
  os.remove(lock_file)

sys.excepthook = excep


# Datos de configuración
config = ConfigParser.RawConfigParser()
config.read(config_file)

host=config.get('config', 'host')
port = config.get('config', 'port')
server=ServerProxy ("https://" + host + ":" + port)
className = config.get('config', 'className')
user = config.get('config', 'user')
password = config.get('config', 'password')
url = config.get('config', 'url')
clave = config.get('config', 'clave')


def busca(uid):
  """ Comprueba si existe el uid del usuario """
  method='get_user_list'
  param_list=[]
  param_list.append((user,password))
  param_list.append(className)
  param_list.append(uid)

  ret=getattr(server,method)(*param_list)

  if len(ret) == 0:
    return False
  else:
    return True

  
def cambia_pass(uid, group, newpass):
  """ Cambia el pass del usuario """
  LDAP_BASE_DN = "dc=ma5,dc=lliurex,dc=net"
  path = "uid=" + uid + ",ou=" + group + ",ou=People," + LDAP_BASE_DN
  method='change_password'
  param_list=[]
  param_list.append((user,password))
  param_list.append(className)
  param_list.append(path)
  param_list.append(newpass)

  ret=getattr(server,method)(*param_list)

  return ret


def process_xml(url):
  """ Procesa la lista de usuarios en XML y devuelve una lista con los datos de los usuarios. """
  xmldoc = minidom.parseString(urllib2.urlopen(url).read())
  # xmldoc = minidom.parse('itaca.xml')
  res = []

  # group puede ser: Students, Teachers, Admins
  
  # Alumnos
  itemlist = xmldoc.getElementsByTagName('alumne')
  for i in itemlist:
    el = {}
    el['group'] = 'Students'
    params = {}
    for node in i.childNodes:
      if node.nodeType != node.TEXT_NODE:
        prop = node.tagName

        if node.firstChild:
          valor = node.firstChild.nodeValue
        else:
          valor = ''

        params[prop] = valor
          
    el['data'] = params
    
    res.append(el)

  # Profesores
  itemlist = xmldoc.getElementsByTagName('professor')
  for i in itemlist:
    el = {}
    el['group'] = 'Teachers'
    params = {}
    for node in i.childNodes:
      if node.nodeType != node.TEXT_NODE:
        prop = node.tagName
        if node.firstChild:
          valor = node.firstChild.nodeValue
        else:
          valor = ''

        params[prop] = valor
          
    el['data'] = params
    
    res.append(el)

  return res


def add_user(data,group):
  """ Añade un usuario a LDAP en el grupo indicado. """

  method='add_user'
  param_list=[]
  param_list.append((user,password))
  param_list.append(className)
  param_list.append(group)
  param_list.append(data)

  ret=getattr(server,method)(*param_list)

  return ret

def decodepass(encoded):
  key = clave
  KEY_SIZE = 16
  BLOCK_SIZE = 32
  padded_key = key.ljust(KEY_SIZE, '\0')

  ciphertext = base64.b64decode(encoded)

  r = rijndael.rijndael(padded_key, BLOCK_SIZE)

  padded_text = ''
  for start in range(0, len(ciphertext), BLOCK_SIZE):
    padded_text += r.decrypt(ciphertext[start:start+BLOCK_SIZE])

  plaintext = padded_text.split('\x00', 1)[0]

  return plaintext

def save_timestamp(f, timestamp):
  with open(f, 'w') as f: f.write(timestamp.strftime("%Y-%m-%d %H:%M:%S\n"))

def main():

  # Comprobamos si el programa está en marcha ya
  if Path(lock_file).is_file():
    print("Programa ya en ejecución")
    return

  # Creamos archivo de lock
  with open(lock_file, 'w') as f: f.write('running')


  # Leemos última fecha y hora de chequeo
  with open(check_file, 'a+') as f: last_check = f.read()

  # Si no existe la fecha, por defecto se toma la fecha y hora actual
  if last_check == '':
    last_check = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S\n")

  # Calculamos los segundos desde el último chequeo hasta la hora actual
  a = datetime.datetime.strptime(last_check, "%Y-%m-%d %H:%M:%S\n")
  b = datetime.datetime.today()

  # Sumamos 30 segundos por seguridad
  secs = int(math.ceil((b-a).total_seconds()) + 30)

  url_full = url + str(secs)

  usuarios = process_xml(url_full)

  for a in usuarios:
    uid = a['data']['uid']
    group = a['group']
    
    # Modificamos campo userPassword
    a['data']['userPassword'] = decodepass(a['data']['userPasswordAlt'])
    del a['data']['userPasswordAlt']
    
    if busca(uid):
      # Si el usuario existe, se cambia su password

      newpass = a['data']['userPassword']

      res  = cambia_pass(uid,group,newpass)
        
      if res == 'true':
        logging.info(u"Se cambia la contraseña para el usuario " + uid + ".\n")
      else:
        logging.error(u"Error al cambiar la contraseña del usuario {0}. Stack: {1}.".format(uid, str(res)))
          
    else:
      # Si el usuario no existe, se crea
      
      res = add_user(a['data'], group)
      
      if "true" in res:
        logging.info(u"Se crea el usuario " + uid + " en el grupo " + group + ".\n")
      else:
        logging.error(u"Error al crear el usuario {0}. Stack: {1}.".format(uid, str(res)))

    time.sleep(1)

  # Actualizamos fecha y hora de la última actualización
  # Sólo si no hay errores al obtener el XML y procesarlo
  save_timestamp(check_file, b)

  # Eliminamos archivo de lock
  os.remove(lock_file)
        
if __name__ == "__main__":
  main()


