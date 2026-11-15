// g = MAJ(a, b, c) AND d, written the naive AIG way: MAJ as an OR of three ANDs.
// Inputs x0..x3 = a, b, c, d.
module top( x0 , x1 , x2 , x3 , y0 );
  input x0 , x1 , x2 , x3 ;
  output y0 ;
  wire n5 , n6 , n7 , n8 , n9 , n10 ;
  assign n5 = x0 & x1 ;
  assign n6 = x0 & x2 ;
  assign n7 = x1 & x2 ;
  assign n8 = ~n5 & ~n6 ;
  assign n9 = n8 & ~n7 ;
  assign n10 = ~n9 & x3 ;
  assign y0 = n10 ;
endmodule
