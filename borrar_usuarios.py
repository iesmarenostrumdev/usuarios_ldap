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

# Para correcta localización de los archivos de log, last_check, etc.
dir = os.path.dirname(os.path.abspath(__file__))

#Archivo para log
log_file = os.path.join(dir, 'usuarios_borrados.log')

# Archivo de configuración
config_file = os.path.join(dir, 'usuarios.config')

# Logs
logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=log_file,level=logging.DEBUG)

def excep(type, value, tb):
  logging.error("Excepción: {0} {1}.".format(str(value), traceback.format_tb(tb)))

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


def delete_user(uid,group):
  """ Borra el usuario uid del grupo group """
  if group == 'Students':
    method='delete_student'
  else:
    method='delete_teacher'

  param_list=[]
  param_list.append((user,password))
  param_list.append(className)
  param_list.append(uid)

  ret=getattr(server,method)(*param_list)

  return ret

def process_xml(archivo):
  """ Procesa la lista de usuarios en XML y devuelve una lista con los datos de los usuarios. """
  xmldoc = minidom.parse(archivo)
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


def main():

  archivo = 'borrar.xml'
  usuarios = process_xml(archivo)

  for a in usuarios:
    uid = a['data']['uid']
    group = a['group']
   
    # Borramos usuario
    res = delete_user(uid,group) 
    logging.info(u"Borrado de usuario {0}. Stack: {1}.".format(uid, str(res)))
          
    time.sleep(1)
        
if __name__ == "__main__":
  main()


