inches=25.4;
bottle_d = 81.75;
tall= 50
;
thick= 1.2;
echo(bottle_d);
$fn=300;
difference(){
    cylinder(d=(bottle_d+thick),tall);
    translate([0,0,thick])cylinder(d=bottle_d,h=tall);
    translate([0,0,-1])cylinder(r=2,h=thick*3);
}