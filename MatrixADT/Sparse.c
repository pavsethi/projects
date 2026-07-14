#include<stdio.h>
#include<stdlib.h>
#include<stdbool.h>
#include<string.h>

#include "List.h"
#include "Matrix.h"


int main(int argc, char * argv[]){                                                            // example taken from FileIO.c

  FILE *in, *out;																			  // input and output file


  // check command line for correct number of arguments
  if( argc != 3 ){  
    fprintf(stderr, "Usage: %s <input file> <output file>\n", argv[0]);
    exit(1);
  }

  // open files for reading and writing 
  in = fopen(argv[1], "r");
  if( in==NULL ){
    fprintf(stderr, "Unable to open file %s for reading\n", argv[1]);
    exit(1);
  }

  out = fopen(argv[2], "w");
  if( out==NULL ){
    fprintf(stderr, "Unable to open file %s for writing\n", argv[2]);
    exit(1);
  }


  int n, a, b;                                                            // n will track size of matrix, a will track A NNZ, b will track B NNZ


  fscanf(in, "%d %d %d", &n, &a, &b);

  Matrix A = newMatrix(n);
  Matrix B = newMatrix(n);

  int r, c;
  double v;                                                            // r will track row, c will track column, v will track value

  for (int i = 1; i <= a; i++){
    fscanf(in, "%d %d %lf", &r, &c, &v);
    changeEntry(A, r, c, v);
  }

  for (int i = 1; i <= b; i++){
    fscanf(in, "%d %d %lf", &r, &c, &v);
    changeEntry(B, r, c, v);
  }

  fprintf(out, "A has %d non-zero entries:\n", a);
  printMatrix(out, A);
  fprintf(out, "\n");

  fprintf(out, "B has %d non-zero entries:\n", b);
  printMatrix(out, B);
  fprintf(out, "\n");

  Matrix C = scalarMult(1.5, A);
  fprintf(out, "(1.5)*A = \n");
  printMatrix(out, C);
  fprintf(out, "\n");

  Matrix D = sum(A, B);
  fprintf(out, "A+B = \n");
  printMatrix(out, D);
  fprintf(out, "\n");


  Matrix E = sum(A, A);
  fprintf(out, "A+A = \n");
  printMatrix(out, E);
  fprintf(out, "\n");

  Matrix F = diff(B, A);
  fprintf(out, "B-A = \n");
  printMatrix(out, F);
  fprintf(out, "\n");


  Matrix G = diff(A, A);
  fprintf(out, "A-A = \n");
  printMatrix(out, G);
  fprintf(out, "\n");

  Matrix H = transpose(A);
  fprintf(out, "Transpose(A) = \n");
  printMatrix(out, H);
  fprintf(out, "\n");


  Matrix I = product(A, B);
  fprintf(out, "A*B = \n");
  printMatrix(out, I);
  fprintf(out, "\n");

  Matrix J = product(B, B);
  fprintf(out, "B*B = \n");
  printMatrix(out, J);
  fprintf(out, "\n");

  freeMatrix(&A);
  freeMatrix(&B);
  freeMatrix(&C);
  freeMatrix(&D);
  freeMatrix(&E);
  freeMatrix(&F);
  freeMatrix(&G);
  freeMatrix(&H);
  freeMatrix(&I);
  freeMatrix(&J);

  return 0;
}

















