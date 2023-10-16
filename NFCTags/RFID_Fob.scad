namefont = "PT Sans:style=Regular";
main_letter_height=2;
size = 10;
t="card";
$fn=99;
base_height = 1.5;
RFID_thick = 1.0;
union(){
    difference(){
       cylinder(d=35,h=base_height);
       translate([0,0,.6])cylinder(d=26,h=RFID_thick);
    }
    translate([-13,-4,base_height])linear_extrude(main_letter_height) 
        text(t,size,font=namefont);
    color("blue")translate([0,0,base_height])difference(){
      cylinder(h=3.2, d=35);
      translate([0,0,1])cylinder(h=5,d=32);
    }
    //loop
    translate([0,19,0])difference(){
        cylinder(d=5,h=base_height+2);
        translate([0,0,-1])cylinder(d=3.5,h=base_height+10);
    }
    }