/*
 * (c) Hellenic Center for Marine Research, 2015
 * 
 * Licensed under the The BSD 2-Clause License; you may not
 * use this file except in compliance with the License.
 * You may obtain a copy of the license at
 * 
 * http://opensource.org/licenses/BSD-2-Clause
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations under
 * the License.
 */

/*
<!--                                            -->
<!--    Script created by Evangelos Pafilis     -->
<!--     as part of the EXTRACT project         -->
<!--              June 2015                     -->
<!--                                            -->
<!--            pafilis@hcmr.gr                 -->
<!--                                            -->

<!------------------------------------------------>
<!--                 History                    -->
<!------------------------------------------------>

<!-- v001: 13.06.15:    added basic browser detection
                        add hyperlinks to identifiers
                        enable ctrl-c / meta-c (keyboard copy event handling)
                        modularized copy-to-clipobard, save-to-file functions
                        displayed firefox/older Chrome non-direct copy to clipboard msgs-->
<!-- v002: 14.06.15:    enables text tag - corresponding entity table row communication
                        the higlight-on-hover occurs bidirectionaly-->
                        
<!-- v003: 15.06.15:    renamed to extract_page.js (formerly extract_iframe.js)
                        finished the  higlight-on-hover by injecting and removing the extract_highlight css style
                        argument in method invocation added: extract_copy_to_clipboard( hidden_text_container_id )
                        -->
<!-- v004: 15.06.15:    fixed the ctrl/meta-c capturing so that it does not affect default
                        browser copy behaviour if text has been selected
                        -->

*/

// configuration
var debug = false;
var deep_debug = false;
var extract_browser = navigator.userAgent;
var hidden_text_container_area_identifier = "clipboard"; //NB: needs by in sync with: <a href="" class="button_link"
                                                        //     onclick="extract_copy_to_clipboard('clipboard');">Copy to clipboard</a>
var is_chrome = extract_browser.toLowerCase().indexOf('chrome') > -1;
var is_firefox = extract_browser.toLowerCase().indexOf('firefox') > -1;
var copy_control_key = "\u2303"; //control key
if (extract_browser.toLowerCase().indexOf('macintosh') > -1) {
    copy_control_key = "\u2318"; //command key
}

//init associative arrays
var give_tag_get_entities = {};
var give_entity_get_tags = {};
var give_entity_get_table_row = {};
var give_table_row_get_entity = {};

if (debug) { console.log( "version: 001, browser: " + extract_browser ); }

///////////////////////////////////////////////////////////////
// main onload event
///////////////////////////////////////////////////////////////

$(document).ready ( function () {
                   extract_display_non_supported_browser_warning();
                   //extract_add_hyperlinks_to_identitiers(); //16.June.2015: functionality moved on the server side
                   extract_enable_higlight_on_hover();
                   extract_enable_ctrl_c_meta_c_event_listener();
                   
                });

///////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////

       
// auxiliary methods 
///////////////////////////////////////////////////////////////
function extract_add_hyperlinks_to_identitiers() {
    var purl_base = "http://purl.obolibrary.org/obo/";
    var ncbi_tax_url_base = "http://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id="
    var anchor_tag_prefix = "<a target ='blank' href='";
    
    var identifier_elements = document.getElementsByClassName("identifier");
    
    var id_text="";
    var identifier_element;
    for (index =0; index < identifier_elements.length; index++)
    {
        identifier_element = identifier_elements[index];
        id_text= identifier_element.innerHTML; 
        if ( /:/.test(id_text) ) {//OBO Ontology term
            identifier_element.innerHTML = anchor_tag_prefix+purl_base+ id_text.replace(":","_") + "'>" + id_text +"</a>";
        }
        if (/^[0-9]+$/.test(id_text)) {//ncbi taxonomy
            identifier_element.innerHTML = anchor_tag_prefix+ncbi_tax_url_base+ id_text + "'>" + id_text +"</a>";
        }
    }
}


function extract_display_non_supported_browser_warning() {
    if (!is_chrome && !is_firefox) {
        alert ( "This popup is best supported in Google Chrome and Mozzila Firefox");
    }
}

function display_manual_copy_message() {
    alert ( "Direct copy to clipboard is not supported by the current version of your browser\n" +
            "Please select the following text manually and then press copy (" + copy_control_key + "-C) "+
            "or use the \"Save to file\" function\n" +
            "\n" +
            document.getElementById('clipboard').innerHTML);
}

function extract_enable_higlight_on_hover (){
    
    //iterate over text tags, assign unique identifiers,
    //attach on mouse over/out events,
    //update tag_entities map (exclude "extract_match" class name), and for each entity add tag
    var text_tag_counter = 1;
    var text_tags = document.getElementsByTagName('span');
    var text_tag;
    for ( tag_index = 0; tag_index < text_tags.length; tag_index++)
    {
        text_tag = text_tags[tag_index];
        var current_text_tag_id = "extract_tag_" + text_tag_counter;
        text_tag.id = current_text_tag_id;
        text_tag.onmouseover = function (){ extract_highlightTableRowsLinkedWithTag( this ); };
        text_tag.onmouseout = function (){ extract_highlight_reset();};
        
        var current_text_tag_entities_string = text_tag.className;
        //exclude "extract_match" class name, the default tag style listed first under class names along with the entities
        current_text_tag_entities_string = current_text_tag_entities_string.replace ("extract_match ", "");
        give_tag_get_entities[ current_text_tag_id ] = current_text_tag_entities_string;
        
        var current_text_tag_entities = current_text_tag_entities_string.split(" ");
        for (ent_idx=0; ent_idx < current_text_tag_entities.length; ent_idx++){
            
            //using the strict equal operator (===), more info on how-to-determine-if-variable-is-undefined
            //http://stackoverflow.com/questions/2647867/how-to-determine-if-variable-is-undefined-or-null
            if (  typeof give_entity_get_tags[ current_text_tag_entities[ent_idx] ]  === 'undefined' )   {
                give_entity_get_tags[ current_text_tag_entities[ent_idx] ] = current_text_tag_id;
            }
            else{
                give_entity_get_tags[ current_text_tag_entities[ent_idx] ] += " " + current_text_tag_id;                
            }
            
        }
        
        text_tag_counter++;
    }
    
    
    //iterate over table cells with identifiers tags,
    //assign unique identifiers,
    //attach on mouse over/out events,
    //update tablerow_entity, and for the entity add tablerow
    var table_row_counter = 1;
    var table_identifier_cells = document.getElementsByClassName('identifier');
    var table_row;

    for ( row_index = 1; row_index < table_identifier_cells.length; row_index++)//start from 1, skip header line
    {
        table_row = table_identifier_cells[row_index].parentNode;
        var current_table_row_id = "extract_tablerow_" + table_row_counter;
        table_row.id = current_table_row_id;
        
        table_row.onmouseover = function (){ extract_highlightTagsLinkedWithTableRowEntity( this ); };
        table_row.onmouseout = function (){ extract_highlight_reset();};
        
        var current_table_row_entity = table_identifier_cells[row_index].textContent;
        give_table_row_get_entity [ current_table_row_id ] = current_table_row_entity;
        give_entity_get_table_row [ current_table_row_entity ] = current_table_row_id;        
        table_row_counter++;
    }    
}

function extract_highlightTableRowsLinkedWithTag( extract_tag_span_elem ){
    if (deep_debug) {
        console.log ("Mouse Over Tag: " + extract_tag_span_elem.id);
        var related_entities_string =  give_tag_get_entities[extract_tag_span_elem.id];
        console.log ("related entities are: " + related_entities_string);
        var related_entities = related_entities_string.split(" ");
        for (curr_ent_idx=0; curr_ent_idx < related_entities.length; curr_ent_idx++){
            console.log ("related table rows are: " + give_entity_get_table_row [  related_entities[curr_ent_idx]   ] );
        }
    }
    
    //highlight current text tag
    add_css_style_to_element( extract_tag_span_elem.id, "extract_highlight");
    
    //highlight linked table rows
    var related_entities_string =  give_tag_get_entities[extract_tag_span_elem.id];
    var related_entities = related_entities_string.split(" ");
    for (curr_ent_idx=0; curr_ent_idx < related_entities.length; curr_ent_idx++){
        add_css_style_to_element ( give_entity_get_table_row [ related_entities[curr_ent_idx] ], "extract_highlight" );
    }
}

function extract_highlightTagsLinkedWithTableRowEntity( extract_table_row_elem ){
    if (deep_debug) {
        console.log ("Mouse Over table row : " + extract_table_row_elem.id);
        console.log ("related entity : " + give_table_row_get_entity [ extract_table_row_elem.id ]);
        console.log ("related tags : " + give_entity_get_tags [ give_table_row_get_entity [ extract_table_row_elem.id ] ]);        
    }
    
    //highlight current table row
    add_css_style_to_element( extract_table_row_elem.id, "extract_highlight");
    
    //highlight linked tags
    var related_tags =  give_entity_get_tags [ give_table_row_get_entity [ extract_table_row_elem.id ] ].split(" ");
    for (rel_tag_idx = 0; rel_tag_idx < related_tags.length; rel_tag_idx++)
    {
        add_css_style_to_element( related_tags[rel_tag_idx], "extract_highlight");
    }

}

function extract_highlight_reset(){
    if (deep_debug) {
        console.log ("Mouse Out");        
    }
    var all_text_tag_spans =  document.getElementsByTagName('span');
    for (tag_span_idx = 0; tag_span_idx < all_text_tag_spans.length; tag_span_idx++)//skip header line
    {
        remove_css_style_from_element( all_text_tag_spans[tag_span_idx].id, "extract_highlight");
    }    
    
    var all_table_rows =  document.getElementsByTagName('tr');
    for (tr_idx = 1; tr_idx < all_table_rows.length; tr_idx++)//skip header line
    {
        remove_css_style_from_element( all_table_rows[tr_idx].id, "extract_highlight");
    }
    
    
}

function add_css_style_to_element(element_id, css_style_class_name){
    if (element_id == "undefined") { console.log( "undef occured" ); return; }
    if (deep_debug) { console.log( "Added style: " + css_style_class_name + " to: " + element_id);    }
    document.getElementById( element_id ).className = document.getElementById( element_id ).className + " " + css_style_class_name;
}

function remove_css_style_from_element(element_id, css_style_class_name){
    if (element_id == "undefined") { return; }
    if (deep_debug) { console.log( "Removed style: " + css_style_class_name + " to: " + element_id);    }
    document.getElementById( element_id ).className = document.getElementById( element_id ).className.replace ( " " + css_style_class_name, "");
}


// event handling methods
//////////////////////////////////////////////////////////////////

function extract_enable_ctrl_c_meta_c_event_listener(){
    document.addEventListener ("keydown", function ( event ) { extract_handle_ctrl_c_meta_c_event ( event ) }, true);
}

function extract_handle_ctrl_c_meta_c_event( event ){

    
    var extract_override_ctrl_meta_c = true;
    var extract_user_selected_text = extract_page_getSelectionText();
    
    if ( extract_user_selected_text || extract_user_selected_text.length > 0 ) {
        //text was selected by the user, you may not overide ctrl/meta-c
        extract_override_ctrl_meta_c = false
    }
    
    if (debug) { console.log ( "Selected text is: *" + extract_user_selected_text+ "*"); }
    if (debug) { console.log ( "Allowed to override ctrl/meta-c ?: " + extract_override_ctrl_meta_c ); }
    
    
    
    if ( extract_override_ctrl_meta_c ) { //process only when no text selected by the user ie do not overide the standard copy
        if (( event.metaKey || event.ctrlKey) &&  event.which == "67" ){//67 => "c"
            if (debug) { console.log ("Keyboard Copy (ctrl-c / meta-c) captured"); }
            if (is_chrome) {
                extract_copy_to_clipboard( hidden_text_container_area_identifier );
            }
            else {
                display_manual_copy_message();
            }
        }
    }
}


// based on the examples found in:
// http://updates.html5rocks.com/2015/04/cut-and-copy-commands and in:
// http://stackoverflow.com/questions/400212/how-do-i-copy-to-the-clipboard-in-javascript
// check answer by Dean Taylor

//read  in the text area name
function extract_copy_to_clipboard( hidden_text_container_id ) {
    
    var copy_to_clipboard_supported = false;

    try {
        document.execCommand('copy');
        copy_to_clipboard_supported = true;
    }
    catch (err) {
        if (debug) { console.log ("copy_to_clipboard not supported"); }
        if (debug) { console.log (err); }
    }
    
    if ( copy_to_clipboard_supported ){
        var clipboard = document.getElementById('clipboard');
        clipboard.style.display = 'block';
        clipboard.select();
        document.execCommand('copy');
        clipboard.style.display = 'none';
    }
    else {
        display_manual_copy_message();
    }
}

function extract_save_to_file( anchor_tag ){
    var data = encodeURIComponent(document.getElementById( hidden_text_container_area_identifier ).innerHTML);
    anchor_tag.setAttribute('href', 'data:text/plain;charset=ascii,'+data)
}


/*
 * method taken from: http://stackoverflow.com/questions/5379120/get-the-highlighted-selected-text
 */
function extract_page_getSelectionText() {
    var text = "";
    if (window.getSelection) {
        text = window.getSelection().toString();
    } else if (document.selection && document.selection.type != "Control") {
        text = document.selection.createRange().text;
    }
    return text;
}


