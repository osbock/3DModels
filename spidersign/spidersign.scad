use <Spider-Man.ttf>
name = "PARKER";
adjustx = 0;
adjusty = 0;
translate([-55,-15,0])import ("spiderman-blank.stl");
color("RED")translate ([28+adjustx,6+adjusty,6])linear_extrude(height = 5)text(name, font = "THE AMAZING SPIDER\\-MAN" ,size = 24);

