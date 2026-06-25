pencil_dia = 7.6;
tolerance = .4;
cone_h =20;


difference(){
    cylinder(d=pencil_dia+2.4+ 2*tolerance, h=50,$fn=6);
    translate([0,0,1.2])cylinder(h=20,d1=0,d2 =pencil_dia+2*tolerance, $fn=50);
    translate([0,0,20])cylinder(h=50, d=pencil_dia+2*tolerance,$fn=6);
    translate([0,0,1.2])cylinder(h=50, d=pencil_dia/2,$fn=40);
    }