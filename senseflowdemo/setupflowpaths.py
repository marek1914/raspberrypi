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
    max_num_flow_servers = 1
    
    # Example:
    # flow_server_url = 'run-west.att.io'
    # flow_base_url = '/83d370c69e410/69332c11db3f/4e73cd2917f04c8/in/flow'

    # Set these 2 variables to point to your own Flow server:    
    flow_server_url =              ######### Set this from your own Flow Endpoint url
    flow_base_url =                ######### Set this from your own Flow Endpoint url
    flow_input_name = "/climate"
    
    # Assign server based upon user selection
    flowurls = [flow_server_url]
    flowpaths = [flow_base_url + flow_input_name]
    
    return flowurls, flowpaths, max_num_flow_servers
