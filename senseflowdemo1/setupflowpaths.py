"""
PI HAT FLOW SENSOR DEMO - flow path config module

   Contributors:
     * Fred Kellerman
 
   Licensed under the Apache License, Version 2.0 (the "License"); 
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, 
   software distributed under the License is distributed on an 
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
   either express or implied. See the License for the specific 
   language governing permissions and limitations under the License.
"""

# Call this function to setup a list of 1 or more Flow servers.
def setup_flow_paths() :

    # Set this to how many different Flow servers you'd like to push data to.
    # There is a limit in the display of max 8.  This could be raised if
    # the main program using this was modified.  For each one you also
    # need to add a set of flow_server_urlx, flow_base_urlx and flow_input_namex
    # vars and add them to the arrays flowurls and flowpaths accordingly!
    max_num_flow_servers = 3
    
    # Base parameters used to connect to the FLOW demo
    flow_server_url1 = 'runm-east.att.io'
    flow_base_url1 = '/ce323678bacc7/d235133ae3dc/0e68c11f947776c/in/flow'
    flow_input_name1 = "/climate"
    
    flow_server_url2 = 'run-west.att.io'
    flow_base_url2 = '/83d370c69e410/69332c11db3f/4e73cd2917f04c8/in/flow'
    flow_input_name2 = "/climate"

    flow_server_url3 = 'run-west.att.io'
    flow_base_url3 = '/0c1d00c85c889/ed9bff332ce2/b4c38cc86ee31bf/in/flow'
    flow_input_name3 = "/climate"
        
    # Assign server based upon user selection
    flowurls = [flow_server_url1, flow_server_url2, flow_server_url3]
    flowpaths = [flow_base_url1 + flow_input_name1, flow_base_url2 + flow_input_name2, flow_base_url2 + flow_input_name3]
    
    return flowurls, flowpaths, max_num_flow_servers
