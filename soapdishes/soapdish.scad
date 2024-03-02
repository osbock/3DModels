inch = 25.4*1; //expressions don't get shown in customizer
width = 225;
length = 200;
//diameter of features
bumpdia = 8;
//cylinders or bumps
cylinder = true;
//ratio of wall height to bump radius
wall_ratio=4;

module bump(){
    $fn=99;
    difference(){
        rotate([0,90,0])cylinder(h=width,d=bumpdia);
        translate([0,-bumpdia/2,-bumpdia/2])cube([width,bumpdia,bumpdia/2]);
    }
}

module rack(){
    intersection(){
        union(){
            cube([width, length, 2]);
            for (y = [0: bumpdia+2 : round(length/bumpdia)*bumpdia]){
                translate([0,y,0])bump();
            }
        }
        cube([width,length,bumpdia/2]);
    }
}
module bumprack(){
    intersection(){
        union(){
            cube([width, length, 2]);
            for (y = [bumpdia+1.5: bumpdia+1.5 : round(length/bumpdia)*bumpdia+bumpdia])
                for(x = [bumpdia+1.5:bumpdia+2:round(width/bumpdia)*bumpdia]){
                translate([x,y,0])cylinder(d1=bumpdia,d2=bumpdia/2, $fn=6,h=bumpdia);
            }
        }
        cube([width,length,bumpdia]);
    }
}
module frame(){
    difference(){
        //minkowski(){
        cube([width,length,(bumpdia/2)*wall_ratio]);
        //cylinder($fn=99,r=.5,h=(bumpdia/2)+4);
        //}
        translate([1.5,1.5,-1])cube([width-3,length-3,(bumpdia/2)+100]);
        }
        }


//soapdish
union(){
   frame();
    if (!cylinder){
        bumprack();
    }
    else{
        rack();
    } 
}
