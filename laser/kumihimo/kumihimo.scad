// Kumihimo disk
outer_dia = 100;
inner_dia = 25;
num_slots = 32;
$fn=99;



difference(){
circle(d=outer_dia);
circle( d=inner_dia);

for (degree = [0:360/num_slots:360]){
    rotate([0,0,degree])translate([-(.75/2), outer_dia/2-8,0])scale([1,9,1])square([.75,9]);
    }


for (count = [num_slots-1:-1:0]){
    rotate([0,0,-count*(360/num_slots)])translate([-1, outer_dia/2-12,0])text(str(count+1), font = ".New York:style=Regular G3",size = 3 );
    }
}
