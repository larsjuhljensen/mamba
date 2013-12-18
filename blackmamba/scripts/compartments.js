
// words to replace
var issues = {
	"Extracellular":"Extracellular space",
	"textmining":"Text mining",
	"ER":"Endoplasmic reticulum",
	"knowledge":"Knowledge",
	"HPA":"Experiments"
	};
	
// white + five colors for confidence values
var datacolors = ["#FFFFFF","#EDF8E9","#BAE4B3","#74C476","#31A354","#006D2C"]; 

// function to get URL parameters
var QueryString = function () {
  // This function is anonymous, is executed immediately and 
  // the return value is assigned to QueryString!
  // later, access via QueryString.something
  var query_string = {};
  var query = window.location.search.substring(1);
  var vars = query.split("&");
  for (var i=0;i<vars.length;i++) {
    var pair = vars[i].split("=");
    	// If first entry with this name
    if (typeof query_string[pair[0]] === "undefined") {
      query_string[pair[0]] = pair[1];
    	// If second entry with this name
    } else if (typeof query_string[pair[0]] === "string") {
      var arr = [ query_string[pair[0]], pair[1] ];
      query_string[pair[0]] = arr;
    	// If third or later entry with this name
    } else {
      query_string[pair[0]].push(pair[1]);
    }
  } 
    return query_string;
} (); 


// retrieve IDs from URL parameters
var orgId = QueryString.type1; //console.log("orgId: "+orgId);
var protId = QueryString.id1; //console.log("protId: "+protId);

// build URL for data request
var jsonURL = "/VisualizationJSON?figure=subcell_overview_%&type="+orgId+"&id="+protId;

// get data for protein/organism
$.getJSON( jsonURL )
    .done(function( data ) {
    	fillCellData(data);
		loadColors(maxValues);
    });
	
var t; // used for timeout on mouseover

function compartment(nom,val,src) {
	this.name = nom;
	this.value = val;
	this.source = src;
}

var cell = []; // all values from various sources
var maxValues = {}; // highest confidence values, to use in drawing

function fillCellData(response) {
	for (r in response){
		var spc = r.indexOf(" ");
		var srce = r.substring(0,spc);
		var comp = r.substr(spc+1);
		//capitalize first letter of compartment name
		var Name = comp.charAt(0).toUpperCase() + comp.substr(1);
		var conf = new compartment(Name,response[r],srce);
		cell.push(conf); //console.log(conf);
		if (!maxValues[comp] || maxValues[comp] < response[r]) { maxValues[comp] = response[r]; }	
	}
}
    
function spellChk(word) {
	//console.log("word "+ word +" is "+ words[word]);
	if (issues[word]) { 
		var chkdWord = issues[word];
		return chkdWord;
	}
	else { 
		return word; 
		}
};

function loadColors(info) {
	//load color values into drawing
	for (f in info) { 
		$(".interactive [title ='"+f+"']").attr("fill", datacolors[info[f]]);
	}
	
	//colorize legend
	$("#Legend rect").each( function(index) {
		$(this).attr("fill", datacolors[parseInt(index)]);
	});
}

$(document).ready( function() {
	// set up interactivity
	$(".interactive").hover( function(event) {
		var myElmt = $(this);
		t = setTimeout(function() { onMoOver(myElmt, event); }, 250);			
	}, function() {
		var myElmt = $(this);
		onMoOut(myElmt);
	});
});

function onMoOver(el, evt) {
	$("div#evidence, div.ruler").remove(); //just in case someone moves too fast
	var ttl = el.attr("title"); //console.log("ttl: "+ttl);
	//blink once	
	el.animate({
		opacity: 0.75
	  }, 200, function() {
		// Animation complete.
		el.animate({
		opacity: 1
		}, 300);
	  }
	);
	//show Labels
	$("#Labels text[title='"+ttl+"']").attr("fill","#000").show();
	//show evidence off to side, parallel to where your mouse entered a compartment
	$("<div id='evidence'><h3></h3></div><div class='ruler'></div>").appendTo(".content");
	$("div#evidence, div.ruler").css("top", evt.pageY+"px");
	$("div.ruler").css({"left":evt.pageX+"px", "width":690-evt.pageX +"px"});
	for (n=0; n<cell.length; n++) {
		if (cell[n].name.toLowerCase() == ttl) {
			$("#evidence h3").text(spellChk(cell[n].name)); //check against "issues" at top
			$("<p><span class='square' style='background:"+datacolors[cell[n].value]+"'>&nbsp;</span>"+spellChk(cell[n].source)+"</p>").appendTo("#evidence"); //check against "issues" at top
			$("div#evidence, div.ruler").show();
		}
	}	
 };

 function onMoOut(el) {	
	var ttl = el.attr("title");
	clearTimeout(t);	
	$("#Labels text").hide();	
	$("div#evidence, div.ruler").remove();
 }
