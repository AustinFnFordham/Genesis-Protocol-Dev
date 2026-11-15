import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
P=Path(__file__).resolve().parent/'deploy/oracle/run.py'
s=importlib.util.spec_from_file_location('oracle',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Pilot(unittest.TestCase):
 def test_writes_refused(self):
  with self.assertRaises(ValueError):m.configure({'GENESIS_MCP_ENABLE_WRITES':'1'})
 def test_missing_mount_refused(self):
  with patch.object(m.Path,'is_mount',return_value=False),self.assertRaises(ValueError):m.configure({})
 def test_config_is_loopback_readonly(self):
  env={'GENESIS_MCP_RESOURCE':'https://genesis-test.duckdns.org/mcp'}
  with patch.object(m.Path,'is_mount',return_value=True):m.configure(env)
  self.assertEqual((env['GENESIS_MCP_HOST'],env['GENESIS_MCP_ENABLE_WRITES']),('127.0.0.1','0'))
 def test_bad_resources_refused(self):
  with patch.object(m.Path,'is_mount',return_value=True):
   for u in ['http://a.duckdns.org/mcp','https://paid.example/mcp','https://u:secret@a.duckdns.org/mcp']:
    with self.subTest(u=u),self.assertRaises(ValueError):m.configure({'GENESIS_MCP_RESOURCE':u})
if __name__=='__main__':unittest.main()
