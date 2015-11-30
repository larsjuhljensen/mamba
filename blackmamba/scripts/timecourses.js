function draw_timecourses(data, container,idName,visible) {
    JSONdata = JSON.parse(data)
    
    var margin = {top: 40, right: 180, bottom: 90, left: 80},
        width = 800 - margin.left - margin.right,
        height = 600 - margin.top - margin.bottom;
    
    var x =d3.scale.linear()
        .range([0, width]);
    
    var y = d3.scale.linear()
        .range([height, 0]);
    
    var color = d3.scale.category10();
    
    var xAxis = d3.svg.axis()
        .scale(x)
        .orient("bottom");
    
    var yAxis = d3.svg.axis()
        .scale(y)
        .orient("left");
    
    var line = d3.svg.line()
        .x(function(d,i) { return x(d[0]); })
        .y(function(d,i) { return y(d[1]); })
    
    svg = d3.select("#" +container).append("svg")
	.attr("class","timec")
	.attr("name",idName)
	.attr("display",function(){return visible?"block":"none";})
	.attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
	
	svg.append("svg:text")
	   .attr("class", "title")
	   .attr("x", -30)
	   .attr("y", -20)
	   .text("Time course experiments");
	 
   color.domain(d3.keys(JSONdata.sources["name"]));
    
    
    var sources = color.domain().map(function(name) {
      return {
        name: name,
        values: values,
	link:link
	
      };
    });
  
    var x_values = function(d,i) {return(d[0]);}
    var y_values = function(d,i) {return(d[1]);}
  
    
    var Xvalues = []
    var Yvalues = []
    JSONdata.sources.forEach(function(entry){
      entry.values.forEach(function(value){
        Xvalues.push(x_values(value))
        Yvalues.push(y_values(value))
      })
    })
    
    x.domain([
      d3.min(Xvalues),
      d3.max(Xvalues)
    ]);
    
    y.domain([
      d3.min(Yvalues),
      d3.max(Yvalues)
    ]);
      
    svg.append("g")
        .attr("class", "x axis")
	.attr("transform", "translate(0," + height + ")")
        .call(xAxis);
  
  
    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("transform", "rotate(-90)")
        .attr("dy", "-1.8em")
        .style("text-anchor", "end")
        .text("Expression");
  
    var source = svg.selectAll(".source")
        .data(JSONdata.sources)
        .enter().append("g")
        .attr("class", "source")
        
    source.append("path")
        .attr("class", "line")
        .attr("div",function(d){return idName+"-"+d.name})
        .attr("d", function(d) { return line(d.values); })
        .style("stroke", function(d) { return color(d.name)})
	//.on("mousemove", function(d) {
	//	var pathLength = this.getTotalLength();
	//	var BBox = this.getBBox();
	//	var scale = pathLength/BBox.width;
	//	var offsetLeft = this.offsetLeft;
	//	var xpoint = d3.event.x - offsetLeft;
	//	var beginning = xpoint, end = pathLength, target;
	//	while (true) {
	//		target =Math.floor((beginning + end)/2);
	//		pos = this.getPointAtLength(target);
	//		if ((target === end || target === beginning) && pos.x !== xpoint) {
	//			break;
	//		}
	//		if (pos.x > xpoint)      end = target;
	//		else if (pos.x < xpoint) beginning = target;
	//		else                break; //position found
	//	}
	//	circle
	//	  .attr("opacity", 1)
	//	  .attr("cx", xpoint)
	//	  .attr("cy", pos.y)
	//	  .attr("stroke", function() { return color(d.name)});})
	;
	
   var circle = svg.append("circle")
      .attr("cx", 100)
      .attr("cy", 350)
      .attr("r", 3)
      .attr("fill","none");
     
   var legend = svg.append("g")
	  .attr("class", "legend")
          .attr("height", 100)
	  .attr("width", 100)
    .attr('transform', 'translate(-20,50)')    
      
    
    legend.selectAll('rect')
      .data(JSONdata.sources.sort(function(a, b){return d3.ascending(a.name,b.name)}))
      .enter()
      .append("rect")
	.attr("name",function(d){return idName+"-"+d.name})
	.attr("x", width +30)
	.attr("y", function(d, i){ return i *  25;})
	.attr("width", 20)
	.attr("height", 20)
	.attr("active","true")
	.style("fill", function(d) { return color(d.name)})
	.style("stroke", function(d) { return color(d.name)})
	.on('mouseover', function(){
	  d3.select(this).style('opacity', 0.35)
	  .style("cursor","pointer")
	})
	.on('mouseleave', function(){
	  d3.select(this).style('opacity', 1)
	})
	.on('click', function(d) {
		rect = d3.select(this)
		act = rect.attr("active") == "true"? "false" : "true";
		col = act =="true"? function() { return color(d.name)}: "white";
		rect.style("fill",col);
		rect.attr("active", act);
		d3.selectAll("path").each(function(f,i){
			var elt = d3.select(this);
			
			if (elt.attr("div") == idName+"-"+d.name){
				var active = this.active? false : true,
				newOpacity = active ? 0 : 1;
				elt.style("opacity", newOpacity);
				this.active = active;
			}
	})});
		
	legend.selectAll('text')
	      .data(JSONdata.sources.sort(function(a, b){return d3.ascending(a.name,b.name)}))
	      .enter()
	     .append("text")
		.style("text-decoration", "underline")  
		.attr("x", width +55)
	      .attr("y", function(d, i){ return i *  25 + 10;})
		.text(function(d) { return d.name;})
		.on("mouseover",function(d){
			d3.select(this)
				.style("cursor","pointer")
		    })
		    .on("mouseout",function(){
			d3.select(this)
				.style('cursor','default')})
		    .on("click",function(d){
			  if (d.link !== undefined) {
			    window.open("http://www.ncbi.nlm.nih.gov/pubmed/?term="+d.link,'_blank');
			  }
			})	  

    return (svg)
  
}
