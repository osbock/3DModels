wallThick = 2;  //sets width of wall at base
cutterMinimum = .2;  //sets width of wall at top
baseHeight = 2;
height = 10;
flangeWidth = 5;

//translate([-22,-275,0])
translate([-2,0,0])union(){
    minkowski(){
    outline();
    cylinder(r1 = wallThick/3, r2 = cutterMinimum/3, h = height);
    };
//%cube([.5, .5, height*3], true);
    
    flange();
    
    }
    translate([-10,14,0])cube([20,5,baseHeight*.7]);
    translate([0,17,0])cylinder($fn=99,d1=5,d2=.2,h=height*1.1);

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
import("ankh-no-hole.dxf");
}