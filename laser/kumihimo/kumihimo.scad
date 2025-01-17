// Kumihimo disk
outer_dia = 100;
inner_dia = 25;
num_slots = 32;
$fn=99;



difference(){
circle(d=outer_dia);
circle( d=inner_dia);

for (degree = [0:360/num_slots:360],count = [1:1:num_slots]){
    rotate([0,0,degree])translate([0, outer_dia/2,0])scale([1,5,1])circle(d=1.5);
    }


for (count = [0:1:num_slots-1]){
    rotate([0,0,count*(360/num_slots)])translate([-1, outer_dia/2-10,0])text(str(count+1), font = ".New York:style=Regular G3",size = 3 );
    }
}
