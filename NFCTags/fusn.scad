$fn=99;
base_height = 2.4;
RFID_thick = 1.2;
union(){

    difference(){
       cylinder(d=35,h=base_height);
       translate([0,0,.6])cylinder(d=26,h=RFID_thick);
    }
    
    color("blue"){
        translate([25,-23,base_height])scale([.2,.2,.2])color("red")linear_extrude(height=9)import(    "fusnchalice.svg");
        color("blue")translate([0,0,base_height])difference(){
            cylinder(h=base_height, d=35);
            translate([0,0,-1])cylinder(h=base_height+3,d=32);
        }
     }
    //loop
    translate([0,18,0])difference(){
        cylinder(h=base_height+1,d=8);
        translate([0,0,-1])cylinder(h=base_height+3,d=6);
        translate([0,-18,-1])cylinder(d=35,h=base_height+3);
        }
    }