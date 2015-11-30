function draw_cycle(data,container) {
  //Function to draw the cycle including the peaktime, icons and protein and transcript averages
  var margin = {top: 10, right: 80, bottom: 30, left: 50},
        width = 800 - margin.left - margin.right,
        height = 800 - margin.top - margin.bottom;
  
  radius = Math.min(width, height) / 2;
  cycle = get_cycle_data(data);
  icons = get_icons(data);
    
  //Get position for icons
  var positions;
  var icons_dict;
  if (icons) {
    icons_dict = get_svg_icons(icons)
    positions = get_phases_position(cycle.cycle_info)
  }
    
  //Draw cycle
  var arc = d3.svg.arc()
    .outerRadius(radius - 60)
    .innerRadius(radius - 130);

  var pie = d3.layout.pie()
    .sort(null)
    .value(function(d) { return d.to - d.from; });

  var svg = d3.select("#" +container).append("svg")
    .attr("class","cycle")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", "translate(" + (width)/ 2 + "," + (height) / 2 + ")");   
    
  var g = svg.selectAll(".arc")
    .data(pie(cycle.cycle_info))
    .enter().append("g")
    .attr("class", "arc");

  g.append("path")
    .attr("d", arc)
    .attr("stroke-width", 2)
    .style("stroke", "black")
    .style("fill",'none')
    
  g.append("text")
    .attr("transform", function(d) { return "translate(" + arc.centroid(d) + ")"; })
    .attr("dy", ".35em")
    .style("text-anchor", "middle")
    .text(function(d) { return d.data.phase; });
    
  //Include text with rank
  if (cycle.rank != "None") {
    svg.append("text")
      .style("text-anchor", "middle")
      .attr("x", 0)
      .attr("y",-30)
      .text("Rank: "+cycle.rank)
  }
  
  //Draw average expression and protein abundance
  draw_average_expression(cycle.average_expression, 155,205,container)
  
  if (!!cycle.average_protein) {
    draw_average_protein(cycle.average_protein, 115, 155,container);
  }
  
  //Draw icons
  var parser = new DOMParser();
  var count = {"G1":0,"S":0,"G2":0,"M":0};
  var labels = {"arrested":"Arrest", "delayed": "Delayed","increasedduration":"Increased duration","decreasedduration":"Decreased duration",
  "abnormalchromosomesegregation":"Abnormal chromosome segregation\n","delayedchromosomesegregation":"Delayed chromosome segregation\n",
  "arrestedchromosomesegregation":"Arrested chromosome segregation\n","abnormalmitoticspindelcheckpoint":"Abnormal mitotic spindel checkpoint\n",
  "ken":"KEN-Box-containing protein","dbox":"D-Box-containing protein","pest":"PEST-containing protein", "cdk":"Phosphotylated by CDK","polo":"Phosphorylated by PLK",
  "nek":"Phosphorylated by NEK","dyrk":"Phosphorylated by DYRK","aurora":"Phosphorylated by Aurora"};
  var known_pos = {"ken": 90, "dbox": 90}
  var out = {"G1":1,"S":1,"G2":1,"M":1};
  for (i in icons_dict){
    var x= 0;
    var y = 0;
    var label = Object.keys(icons_dict[i]).pop();
    var phase = label.split("_")[0]
    var pheno = label.split("_")[2]
    
    var pos = positions[phase];
    
    if (pheno in labels) {
      pheno = labels[pheno];
    }
    
    
    //position the icon according to which percentage of the cycle it is in
    if (pos >0 && pos < 25) {
      x=-15;
      y=-55;
    }
    else if(pos==25){
      x=-16;
      y=-65;
    }
    else if(pos>25 && pos<40){
      x=-10;
      y=-25;
    }
    else if (pos >= 50 && pos < 60) {
      x=-95;
    }
    else if (pos >= 60 && pos < 75) {
      x=-70;
      y=-40;
    }
    else if (pos >= 75 && pos < 90) {
      x=-55;
      y=-55;
    }
    else if (pos >= 90 && pos < 100) {
      x=-25;
      y=-70;
    }
    
    var coord = get_coordinates(pos/100,x,y,radius-60);
    x = coord.x
    y = coord.y
    // if more than one icon in one phase add an offset
    if (count[phase] > 0) {
      x = (phase == "G1" || phase == "S")? x+count[phase] : x-count[phase];
    }
    
    //check the width is not exceeded 
    if(width/2+x<0){
	x = x+out[phase]*75;
	y= y - 65;
	out[phase] +=2;
    }
    else if(width/2+x>=width-75){
	x = x-out[phase]*75;
	y= y - 65;
	out[phase] +=2;
    }
    var svgDoc = parser.parseFromString(icons_dict[i][label], "text/xml");
    var svgXML=svgDoc.documentElement 
    var svgObj =document.adoptNode(svgXML);
    
    var icon_g = svg.append('g')
    .attr("transform", "translate("+x+","+y+")")
    .attr("label",pheno+" in "+phase+" phase")
    .on("mouseover",function(){sel = d3.select(this);
	label = sel.attr("label");
	sel.attr('opacity',0.8)
	sel.append("title").attr("transition-delay","0s").text(label)})
    .on("mouseout",function(){sel = d3.select(this);
	sel.attr('opacity',1)});
    
    
    //Add icon to orginal svg
    icon_g[0][0].appendChild(svgObj)
    count[phase] += 75
  }
  
  //Draw Peaktime according to Microarray experiments
  if (cycle.peaktime != "None") {
    coord_target = get_coordinates(cycle.peaktime/100,0,0,radius-130);
    coord_source = get_coordinates(cycle.peaktime/100,0,0,(radius-130)/1.325);
    
    svg.append("svg:defs").append("svg:marker")
      .attr("id", "arrow")
      .attr("value",cycle.peaktime)
      .attr("viewBox", "0 0 10 11")
      .attr("refX", 9)
      .attr("refY", 5)
      .attr("markerUnits", "strokeWidth")
      .attr("markerWidth", 5)
      .attr("markerHeight", 5)
      .attr("orient", "auto")
      .style("fill","red")
      .append("svg:path").attr("d", "M 0 0 L 10 5 L 0 10 z");
      
    svg.append("line")
    .style("stroke", "red")
    .attr("value",cycle.peaktime)
    .attr("stroke-width", 3.5)
    .attr("marker-end", "url(#arrow)")
     .on("mouseover",function(){sel = d3.select(this);
	sel.style('stroke-width',5)
	label = "peaktime: "+sel.attr("value")+"% of the cell cycle";
	sel.append("title").text(label)})
    .on("mouseout",function(){sel = d3.select(this);
	sel.style('stroke-width',3.5)});
  
   svg.selectAll("line").attr("x1", function(d){
	return coord_source.x;
      }).attr("y1", function(d){
	return coord_source.y;
      }).attr("x2", function(d){
	return coord_target.x;
      }).attr("y2", function(d){
	return coord_target.y;
      }).attr("marker-end", "url(#arrow)");
  }
}

function get_proteomic_bucket(phase){
  phases = {"G1" : [0,36],"G1/S":[36,49],"Early S":[49,55],"Late S" : [55,65],"G2":[65,85],"M" : [85,100]}
  return {
    start: phases[phase][0],
    end: phases[phase][1]
  };
}

function draw_average_protein(sources_data, innerRadius, outterRadius,container){
  var colours = ["#fff7fb","#ece7f2","#d0d1e6","#a6bddb","#74a9cf","#3690c0","#0570b0","#045a8d","#023858"];
  var legend_colors = ["#fff7ec","#fdbb84","#d7301f","#ff0000"];
  var name = "avg_protein"
  var label = "Proteomics experiments\naverage ratio of intensity: ";
  phases = sources_data['phases']
  sources = sources_data['sources']
  
  var average = [0,0,0,0,0,0];
  var individual_values = ["","","","","",""]
  var count = 0
  var url = undefined
  sources.forEach(function(d){
      source_name = d["name"]
      ratios = d["values"]
      values = average
      if (d["url"] !== undefined && url == undefined) {
	url = d["url"];
      }
      i = 0
      ratios.forEach(function(e){
	if (individual_values[i] == "") {
	  individual_values[i] = source_name+": "+e.toFixed(2)
	}
	else{
	  individual_values[i] = "\n"+individual_values[i]+"\n"+source_name+": "+e.toFixed(2)  
	}
	i+=1;
	})
      i = 0
      values.forEach(function(f){
	  average[i] = f+ratios[i];
	  i+=1;
	})
      count+=1;
    })
  
  i = 0;
  if (count>1) {
    average.forEach(function(d){
      average[i] = average[i]/count;
      i +=1;
      })
  }
  
  minValue = Math.min.apply(Math,average)
  maxValue = Math.max.apply(Math,average)
  
  var average_data = []
  var i = 0
  phases.forEach(function(d){
      var bucket = get_proteomic_bucket(d);
       average_data.push({phase: d, start: bucket.start,end: bucket.end,value:average[i],linkout:url,label:individual_values[i]});
       i += 1;
    })  
  
  draw_gradient_cycle(average_data, name,innerRadius, outterRadius,minValue,maxValue,label,colours,2.2)
  
}

function draw_average_expression(average, innerRadius,outterRadius,container){
  minValue = Math.min.apply(Math,average)
  maxValue = Math.max.apply(Math,average)
  
  var colours = ["#fff7fb","#ece7f2","#d0d1e6","#a6bddb","#74a9cf","#3690c0","#0570b0","#045a8d","#023858"];
  var legend_colors = ["#fff7fb","#ece7f2","#d0d1e6","#a6bddb","#74a9cf","#3690c0","#0570b0","#045a8d","#023858"]
  var name = "avg_expression";
  var label = "Microarrays experiments\naverage expression: ";
  
  var i= 0;
  var average_data = []
  average.forEach(function(d) {
    var start = i *(2*Math.PI/100);
    var end = (i+1)*(2*Math.PI/100);
    i +=1;
    average_data.push({start: start,end: end,value:d,label:d.toFixed(2),linkout:undefined});
  });

  draw_gradient_cycle(average_data,name,innerRadius, outterRadius,minValue,maxValue,label,colours,1.5)
  
  var svg = d3.selectAll(".cycle").select('g')
  
  svg.selectAll("rect")
      .data(legend_colors)
       .enter().append("rect")
       .attr("class",name)
      .attr("x",  function(d, i){ return -65+(i *  15);})
      .attr("y", 32)
      .attr("width", 15)
      .attr("height", 15)
      .style("stroke","black")
      .style("fill", function(d) { 
         return d;
      });
    svg.append('text')
      .attr("class",name)
      .attr("x", -34)
      .attr("y",30)
      .text("Expression")
  
}

function draw_gradient_cycle(average,name,innerRadius, outterRadius,minValue,maxValue,title,colours,factor){
  var colorScale = d3.scale.linear()
     .domain(d3.range(minValue, maxValue, factor / (colours.length - 1)))
      .range(colours);

  var svg = d3.selectAll(".cycle").select('g')
  
  var arc = d3.svg.arc()
    .innerRadius(innerRadius)
    .outerRadius(outterRadius)
      
  var pie = d3.layout.pie()
    .sort(null)
    .value(function(d) {return d.end-d.start; });
  
  var g = svg.selectAll("."+name)
    .data(pie(average))
    .enter().append("g")
    .attr("class", name);

  var path = g.append("path")
    .attr("d", arc)
    .attr("stroke-width", 2)
    .style("stroke",'none')
    .style("fill", function(d) { return colorScale(d.data.value);})
    .on("mouseover",function(d){sel = d3.select(this);
	this.parentNode.appendChild(this)
	label = title+d.data.label;
	sel.style('stroke',"#fd8d3c")
	sel.append("title").text(label)
	if (d.data.linkout !== undefined) {
	  sel.style("cursor","pointer")
	}
    })
    .on("mouseout",function(){sel = d3.select(this);
	sel.style('stroke','none')
	.style('cursor','default')})
    .on("click",function(d){
	  if (d.data.linkout !== undefined) {
	    window.open(d.data.linkout,'_blank');
	  }
	});
}

function get_svg_icons(icons){
    var parser = new DOMParser();
    var icon_dict = {};
    for (i in icons){
      label = Object.keys(icons[i]).pop()
      svgStr = icons[i][label];
      
      var svgDoc = parser.parseFromString(svgStr, "text/xml");
      var svgXML=svgDoc.documentElement 
      var svgObj =document.adoptNode(svgXML);
      
      icon_dict[label] = svgObj;
      
    }
    return icons
}

function get_phases_position(cycle_info){
    var positions = {};
    var prev_phase;
    for (i in cycle_info){
	var phase = cycle_info[i]["phase"];
	var from = cycle_info[i]["from"];
	var to = cycle_info[i]["to"];
	positions[phase] = from +(to - from)/2;
	if (prev_phase) {
	  positions[prev_phase+"/"+phase] = from;
	}
	prev_phase = phase;
    }
    
    return positions;
}

function get_icons(data){
    var parsed_jSON = JSON.parse(data);
    var icons
    if ("icons" in parsed_jSON) {
      icons = parsed_jSON["icons"];
    }
    return icons;
}

function get_coordinates(p,x0,y0,r) {
  var x= r * Math.cos(2*Math.PI*p-Math.PI/2) + x0;
  var y= r * Math.sin(2*Math.PI*p-Math.PI/2) + y0;
  return {
    x: x,
    y: y
  }
}

function get_cycle_data(data){
    var parsed_jSON = JSON.parse(data);
    var combined_results = parsed_jSON["results"][0];  
    var peaktime = combined_results["combined"]["peak"];
    var rank = combined_results["combined"]["rank"];
    var avg_expression = combined_results["combined"]["average_expression"];
    var avg_protein = null
    if (combined_results["combined"]["average_protein"] != undefined) {
      avg_protein = combined_results["combined"]["average_protein"];
    }
    var cycle_info = parsed_jSON["cycleinfo"];
    
    return {
	peaktime : peaktime,
	rank : rank,
	average_expression: avg_expression,
	average_protein: avg_protein,
	cycle_info : cycle_info
    }
}

function build_time_course_queries(data,container) {
  var obj = JSON.parse(data);
   
  var individual_results = obj["results"][1];
  
  var visible_probeset = "";
  var hidden_probesets = {};
  var list_sources = {};
  var ops = [];
  queries = [];
  
  for (rec in individual_results["individual"]){
    var probeset = individual_results["individual"][rec]["id"];
    var source = individual_results["individual"][rec]["source"];
    list_sources[source] = 1;
    var show = individual_results["individual"][rec]["visible"];
    if (show === "t") {
      visible_probeset = probeset;
    }
    else{
      hidden_probesets[probeset] = 1;
    }
  }
  var ids = Object.keys(hidden_probesets)
  var sources = Object.keys(list_sources).join(',')
  
  
  queries.push("id="+visible_probeset+"&sources="+sources)
  
  if (ids.length > 0) {
    ids.forEach(function(d){
       queries.push("id="+d+"&sources="+sources);
     })
     
    ops.push("multiple probesets found")
    ops.push(visible_probeset)
    ops.push.apply(ops,ids)
    var select = d3.select('#'+container)
	  .append('select')
	  .attr('class','select')
	  .on('change',onchange)
    var options = select
	  .selectAll('option')
	  .data(ops).enter()
	  .append('option')
		  .text(function (d) { return d; });
		  
    select.select('option').attr('disabled','disabled')
  }
   return queries;
}

function onchange() {
	selectValue = d3.select('select').property('value')
	d3.selectAll('.timec').each(function(d){
	  var sel = d3.select(this)
	  if(sel.attr('name') === selectValue){
	    sel.attr("display","block");
	  }
	  else{
	    sel.attr("display","none")
	  }
	})
};

function add_cyle_axis(cycleinfo,peaktime,name,container) {
    
    var svg = null;
    d3.selectAll(".timec").each( function(){
	var sel = d3.select(this);
	if(sel.attr("name") == name){
	  svg = sel;
	}
  })
    var g = svg.select("g")
    var current_xaxis = g.select("g.x.axis")
    var ticks = current_xaxis.selectAll("g.tick")
    var path = current_xaxis.select("path")
    
    
    ticks
      .style("opacity", 0)
    
    var initial_position = parseFloat(ticks.attr("transform").split("(")[1].split(",")[0])
    var last_tick = ticks[0][ticks[0].length-1].getAttribute("transform");
    var last_position = parseFloat(last_tick.split("(")[1].split(",")[0])
    
    var translate1 = current_xaxis.attr("transform")
    var attr_path = path.attr("d")
    var widthmax = parseInt(attr_path.split("H")[1].split("V")[0])
    
    attr_path = attr_path.replace(widthmax.toString(),(widthmax+5).toString())
    attr_path = attr_path.replace("M0","M-5")
    
    //var distance = ticks[0][1].__data__ - parseInt(ticks[0][0].__data__)
    var distance = widthmax - last_position
    var xmax = ticks[0][ticks[0].length-1].__data__ + distance
    
    var xstart = parseInt(ticks[0][0].__data__) - (initial_position*xmax/widthmax)
    
    var data = generate_cycles(cycleinfo,xstart, xmax)
    
    var extra_axis = g.append("g")
      .attr("class", "extra_axis")
      .attr("transform", translate1)
    
    var prev_width = 0
    extra_axis.selectAll('rect')
      .data(data)
      .enter()
      .append("rect")
      .attr("name",function(d){return d.phase})
      .style("stroke", "black")
      .style("fill","white")
      .attr("x", function(d){
                              var new_pos = prev_width;
			      prev_width += (d.to - d.from)*widthmax/(xmax-xstart);
                              return new_pos})
      .attr("y", 30)
      .attr("width", function(d){return (d.to - d.from)*widthmax/(xmax-xstart);})
      .attr("height", 15)
      
      var prev_width = 0
      extra_axis.selectAll('text')
          .data(data)
          .enter()
          .append("text")
          .attr("x", function(d, i){
                              var new_pos = (prev_width+((d.to - d.from)*widthmax/(xmax-xstart))/2)-5;
                              prev_width += (d.to - d.from)*widthmax/(xmax-xstart);
                              return new_pos})
          .attr("y",60)
          .text(function(d) { return d.phase;})
      extra_axis.append("path")
	.attr("d",attr_path)
	.attr("fill","white")
	.attr("transform","translate(0,29)")
	
	
      if (peaktime !== "None") {
	var num_cycles = xmax/100;
	var cycle = 0;
	var peak = parseInt(peaktime)
	while(num_cycles >0){
	  var new_peak = peak + cycle - xstart;
	  if (new_peak>= 0 && new_peak <= (xmax-xstart)) {
	    extra_axis.append("circle")
	    .attr("value",peak)
	    .attr("cx",function(){return new_peak*widthmax/(xmax-xstart);})
	    .attr("cy",37.5)
	    .attr("r",3)
	    .style("fill","red")
	    .on("mouseover",function(){sel = d3.select(this);
	      sel.attr('r',4);
	      label = "peaktime: "+sel.attr("value")+"% of the cell cycle";
	      sel.append("title").text(label);})
	    .on("mouseout",function(){sel = d3.select(this);
	      sel.attr('r',3);});
	  }
	  num_cycles--;
	  cycle +=100;
	}
      }
}

function generate_cycles(data,start, max) {
  var start_index = 0;
  var initial_phase = 0;
  data.forEach(function(p){
      if (p.from<= start && p.to > start) {
        initial_phase = start_index;
      }
      start_index++;
  });
  
  var object = new Array();
  var num_cycles = (max)/100;
  var num_phases = 4;
  var cycle = 0;
  var distance = 0
  var first = true
  while (num_cycles > 0) {
    i = initial_phase;
    while(i < num_phases){
      var o = clone(data[i]);
      if (num_cycles < 1) {
        distance += data[i].to - data[i].from
        if (distance > num_cycles*100) {
	  diff = (data[i].to - data[i].from)-(distance - num_cycles*100)
          o.from = cycle + data[i].from
	  o.to = cycle + data[i].from + diff;
	  object.push(o);
	  break;
        }
      }
      if (first) {
	o.from = start;
	first = false;
      }
      else{
	o.from = cycle + data[i].from;
      }
      o.to = cycle + data[i].to;
      object.push(o);
      i++;
    }
    num_cycles--; 
    cycle =cycle + 100;
    initial_phase = 0;
  }
  return(object);
}

function clone(obj) {
    var result = {};
    for (var key in obj) {
        result[key] = obj[key];
    }
    return result;
}
