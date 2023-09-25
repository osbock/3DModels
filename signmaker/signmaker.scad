
/*
Phantom Fingers font found at:
https://www.1001fonts.com/phantom-fingers-font.html

Note that the Fill function requires the development release of OpenSCAD
https://openscad.org/downloads.html#snapshots
*/

text = "Danger!";
size = 20;

namefont = "Phantom Fingers:style=Regular";
main_letter_height=6;

module sign(t =text){
union(){
    linear_extrude(main_letter_height) 
        text(t,size,font=namefont);
    color("darkslategray") {
        linear_extrude(1) {
            offset(size/6) {
                fill() {
                    text(t,size, font=namefont);
                }
            }
        }
    }
    }
}
sign(text);
/*
//custom kerned multi-line sign example
size =9;
main_letter_height=2;
union(){
translate([0,0,0])sign("Problem");
translate([63,0,0])sign("Sol");
translate([84,0,0])sign("ving");
translate([23,-22,0])sign("isMyDrug");
translate([23,-44,0])sign("ofChoice");
color("darkslategray")translate([58,-15,0])cylinder(h=1,d=50);
}
*/