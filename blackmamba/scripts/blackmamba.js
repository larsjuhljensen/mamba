// =============================================================================
// Ajax stuff.
// =============================================================================
function blackmamba_xmlhttp()
{
	if (window.XMLHttpRequest) {
		return new XMLHttpRequest();
	}
	else if (window.ActiveXObject) {
		return new ActiveXObject("Microsoft.XMLHTTP");
	}
}


function blackmamba_request(xmlhttp, url, query, container)
{
	xmlhttp.open(query == "" ? "GET" : "POST", url, true);
	xmlhttp.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xmlhttp.onreadystatechange = function() {
		if (xmlhttp.readyState == 4) {
			div = document.getElementById(container)
			div.innerHTML = xmlhttp.responseText;
			div.style.visibility = 'visible';
		}
	}
	xmlhttp.send(query);
	try {
		_gaq.push(['_trackPageview', url]);
	}
	catch (err) {
	}
}


// =============================================================================
// Black mamba stuff.
// =============================================================================

function blackmamba_search(url, section, limit, page, container)
{
	div = document.getElementById(container)
	div.innerHTML = "<H3>Searching</H3><p>Fetching results for page "+page+". Please wait ...</p>"
	form = document.blackmamba_search_form;
	query = "query="+escape(form.query.value)
	if (section != "") {
		query += "&section="+section
	}
	query += "&limit="+limit+"&page="+page+"&container="+container
	blackmamba_request(blackmamba_xmlhttp(), url, query, container);
}

function blackmamba_visualization(url, channel, figure, type, id)
{
	blackmamba_request(blackmamba_xmlhttp(),  url, "figure=" + escape(figure) + "&type=" + type + "&id=" + escape(id), "blackmamba_" + channel + "_div");
}

function blackmamba_header(type, id, container)
{
	blackmamba_request(blackmamba_xmlhttp(), "PopupHeader", "type="+type+"&id="+id, container);
}

function blackmamba_pager(url, query, limit, page, container)
{
	div = document.getElementById(container);
	div.innerHTML = '<p>Fetching ...</p>';
	div.style.visibility = 'visible';
	blackmamba_request(blackmamba_xmlhttp(), url, query+"&limit="+limit+"&page="+page+"&container="+escape(container), container);
}


// =============================================================================
// Textmining-table: Expand, collapse teaser vs. whole abstract text.
// =============================================================================

function close_popup()
{
	document.getElementById('blackmamba_popup').style.visibility = 'hidden';
	document.getElementById('blackmamba_popup_header').innerHTML = '';
	document.getElementById('blackmamba_popup_body').innerHTML = '';
}

function open_popup()
{
	document.getElementById('blackmamba_popup').style.left = 50;
	document.getElementById('blackmamba_popup').style.top = window.pageYOffset+50;
	document.getElementById('blackmamba_popup').style.visibility = 'visible';
}

function toggle_document_abstract(document_id, action)
{
	divs = $("#" + document_id + " .document_abstract div");
	el1 = divs[0];
	el2 = divs[1];
	if (action == "expand") {
		$(el1).addClass("hidden");
		$(el2).removeClass("hidden");
	}
	else {
		$(el1).removeClass("hidden");
		$(el2).addClass("hidden");
	}
}

document.onkeydown = function(e) {
    e = e || window.event;
    if (e.keyCode == 27) {
	close_popup();	
    }
};
