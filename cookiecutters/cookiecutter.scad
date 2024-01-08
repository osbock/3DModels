wallThick = 2;  //sets width of wall at base
cutterMinimum = .2;  //sets width of wall at top
baseHeight = 2;
height = 10;
flangeWidth = 5;


translate([-22,-275,0])union(){
    minkowski(){
    outline();
    cylinder(r1 = wallThick/3, r2 = cutterMinimum/3, h = height);
    };
//%cube([.5, .5, height*3], true);
    
    flange();
    
    }
    translate([-5,-30,0])cube([10,55,baseHeight*.7]);

module flange(){
	difference(){
	minkowski(){
	baseShape(baseHeight/3);
	cylinder(r = flangeWidth, h = baseHeight/3);
	}
	translate([0,0,-0.01])baseShape(baseHeight*1.1);
	};
}



module outline(){
	difference(){
	minkowski(){
	baseShape(baseHeight/3);
	cylinder(r = cutterMinimum/3, h = baseHeight/3);
	}
	translate([0,0,-0.01])baseShape(baseHeight*1.1);
	};
};

module baseShape(H){
linear_extrude(height=H)
import("cross.dxf");
}