//Penholder for eye dropping

$fn=99;
base_dia=40;
pen_dia=10.5; //Pilot varsity

upper_dia = pen_dia+10;
tolerance = .5;

difference(){
    cylinder(d1=base_dia,d2=upper_dia, h= 30);
    union(){
       translate([0,0,7])cylinder(d=pen_dia+tolerance, h= 100);
       translate([0,0,7])sphere(d=pen_dia+tolerance);
       }
    }