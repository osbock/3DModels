$fn=99;
base_height = 1.5;
RFID_thick = 1.0;
union(){
    difference(){
       cylinder(d=35,h=base_height);
       translate([0,0,.6])cylinder(d=26,h=RFID_thick);
    }
    translate([-15,-55,base_height])scale([.2,.2,.2])color("red")linear_extrude(height=12)import("cof.svg");
    color("blue")translate([0,0,base_height])difference(){
      cylinder(h=3.2, d=35);
      translate([0,0,1])cylinder(h=5,d=32);
    }
    }