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

function blackmamba_timecourses_request(xmlhttp, url, query, container,name,visible,async)
{
	xmlhttp.open(query == "" ? "GET" : "POST", url, async);
	xmlhttp.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xmlhttp.onreadystatechange = function() {
		if (xmlhttp.readyState == 4) {
			draw_timecourses(xmlhttp.responseText, container,name, visible);
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

function blackmamba_cyclebase_cycle_request(xmlhttp, url, query, container)
{
	xmlhttp.open(query == "" ? "GET" : "POST", url, true);
	xmlhttp.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xmlhttp.onreadystatechange = function() {
		if (xmlhttp.readyState == 4){
			var response = xmlhttp.responseText;
			draw_cycle(response ,container);
			
		}
	}
	xmlhttp.send(query);
	try {
		_gaq.push(['_trackPageview', url]);
	}
	catch (err) {
	}
}

function blackmamba_cyclebase_timecourse_request(xmlhttp, url, query, container)
{
	xmlhttp.open(query == "" ? "GET" : "POST", url, true);
	xmlhttp.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
	xmlhttp.onreadystatechange = function() {
		if (xmlhttp.readyState == 4){
			var response = xmlhttp.responseText;
			var cycle = get_cycle_data(response);
			var queries = build_time_course_queries(response,container);
			visible = true;
			queries.forEach(function(d){
				var name = d.split("=")[1].split("&")[0]
				blackmamba_timecourses(d,container,name,visible,false);
				visible = false;
				add_cyle_axis(cycle.cycle_info,cycle.peaktime,name,container);
				})
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
	div = document.getElementById(container);
	div.innerHTML = "<H3>Searching</H3><p>Fetching results for page "+page+". Please wait ...</p>";
	form = document.blackmamba_search_form;
	query = "query="+escape(form.query.value);
	window.history.pushState(null, null, window.location.href.split("?")[0]+"?"+query);
	if (section != "") {
		query += "&section="+section
	}
	query += "&limit="+limit+"&page="+page+"&container="+container;
	blackmamba_request(blackmamba_xmlhttp(), url, query, container);
}

function blackmamba_advanced_search(url, section, limit, page, container)
{
	div = document.getElementById(container)
	div.innerHTML = "<H3>Searching</H3><p>Fetching results for page "+page+". Please wait ...</p>"
	form = document.blackmamba_advanced_search_form;
	query = ""
	id = "id="+escape(form.id.value)
	type  = "type="+escape(form.organisms.value)
	phase  = "phase="+escape(form.phase.value)
	rank  = "rank="+escape(form.rank.value)
	phenotype = "phenotype="+escape(form.phenotype.value)
	query += id+"&"+type+"&"+phase+"&"+phenotype+"&"+rank+"&limit="+limit+"&page="+page+"&container="+container
	if (section != "") {
		query += "&section="+section
	}
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

function blackmamba_timecourses(query, container,name,visible,async)
{
	div = document.getElementById(container);
	div.style.visibility = 'visible';
	blackmamba_timecourses_request(blackmamba_xmlhttp(), "TimeCourses", query, container,name,visible,async);
}

function blackmamba_cyclebase_cycle(query, container)
{
	div = document.getElementById(container);
	div.style.visibility = 'visible';
	blackmamba_cyclebase_cycle_request(blackmamba_xmlhttp(), "Cyclebase", query, container);
}

function blackmamba_cyclebase_timecourse(query, container)
{
	div = document.getElementById(container);
	div.style.visibility = 'visible';
	blackmamba_cyclebase_timecourse_request(blackmamba_xmlhttp(), "Cyclebase", query, container);
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
