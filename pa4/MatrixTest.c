/********************************************************************************* 
* Pav Sethi, pssethi
* 2023 Winter CSE101 PA #4
* MatrixTest.c
* Tests each individual function for Matrix ADT 
*********************************************************************************/ 
#include<stdlib.h>
#include<stdio.h>
#include<stdbool.h>
#include"Matrix.h"
     
int main(){
   int n=10;
   Matrix A = newMatrix(n);
   Matrix B = newMatrix(n);
   Matrix C;
   Matrix D;


   printf("\n");
   printf("----------------TESTING empty size and NNZ-------------------------\n");

   if (size(A) == 10) {
      printf("Matrix empty size Test: PASSED\n");
   } else {
      printf("Matrix empty size Test: FAILED\n");
   }

   if (NNZ(A) == 0){
      printf("Matrix empty NNZ Test: PASSED\n");
   } else {
      printf("Matrix empty NNZ Test: FAILED\n");
   }



   printf("\n");
   printf("----------------TESTING nonempty size and NNZ-------------------------\n");

   changeEntry(A, 1, 1, 4);
   changeEntry(A, 1, 2, 2);
   changeEntry(A, 1, 3, 0);
   changeEntry(A, 2, 1, 2);
   changeEntry(A, 3, 1, 0);
   changeEntry(A, 2, 2, 2);
   changeEntry(A, 3, 3, 0);

   if (size(A) == 10) {
      printf("Matrix nonempty size Test: PASSED\n");
   } else {
      printf("Matrix nonempty size Test: FAILED\n");
   }

   if (NNZ(A) == 4) {
      printf("Matrix nonempty NNZ Test: PASSED\n");
   } else {
      printf("Matrix nonempty NNZ Test: FAILED\n");
   }


   printf("\n");
   printf("----------------TESTING makeZero-------------------------\n");

   makeZero(A);

   if (NNZ(A) == 0) {
      printf("Matrix makeZero Test: PASSED\n");
   } else {
      printf("Matrix makeZero Test: FAILED\n");
   }


   printf("\n");
   printf("----------------TESTING changeEntry-------------------------\n");

   changeEntry(A, 1, 1, 4);
   changeEntry(A, 1, 2, 2);
   changeEntry(A, 1, 3, 0);
   changeEntry(A, 2, 1, 2);
   changeEntry(A, 3, 1, 0);
   changeEntry(A, 2, 2, 2);
   changeEntry(A, 3, 3, 0);

   if (NNZ(A) == 4) {
      printf("Matrix changeEntry Test 1: PASSED\n");
   } else {
      printf("Matrix changeEntry Test 1: FAILED\n");
   }

   changeEntry(A, 5, 2, 3);
   changeEntry(A, 4, 1, 8);
   changeEntry(A, 6, 4, 9);
   changeEntry(A, 1, 1, 0);
   changeEntry(A, 2, 1, 0);
   changeEntry(A, 3, 3, 0);
   changeEntry(A, 2, 2, 0);

   if (NNZ(A) == 4) {
      printf("Matrix changeEntry Test 2: PASSED\n");
   } else {
      printf("Matrix changeEntry Test 2: FAILED\n");
   }


   printf("\n");
   printf("----------------TESTING copy()-------------------------\n");

   C = copy(A);

   printf("%d\n", NNZ(C));
   if (NNZ(C) == 4) {
      printf("Matrix copy Test 1: PASSED\n");
   } else {
      printf("Matrix copy Test 1: FAILED\n");
   }

   changeEntry(A, 1, 1, 4);

   if (NNZ(C) == 4) {
      printf("Matrix copy Test 2: PASSED\n");
   } else {
      printf("Matrix copy Test 2: FAILED\n");
   }


   printf("\n");
   printf("----------------TESTING transpose()-------------------------\n");

   D = transpose(A);

   if (NNZ(C) == 4) {
      printf("Matrix transpose Test 1: PASSED\n");
   } else {
      printf("Matrix transpose Test 1: FAILED\n");
   }

   printf("\n");

   printMatrix(stdout, A);
   printf("\n");

   printMatrix(stdout, D);
  
   printf("\n");
   printf("----------------TESTING sum()-------------------------\n");

   freeMatrix(&C);
   freeMatrix(&D);

   makeZero(A);

   changeEntry(A, 1,1,1); 
   changeEntry(A, 1,2,2);
   changeEntry(A, 1,3,3); 
   changeEntry(A, 2,1,4);
   changeEntry(A, 2,2,5);
   changeEntry(A, 2,3,6);
   changeEntry(A, 3,1,7); 
   changeEntry(A, 3,2,8); 
   changeEntry(A, 3,3,9);

   C = sum(A, A);

   if (NNZ(C) == 9) {
      printf("Matrix sum Test 1: PASSED\n");
   } else {
      printf("Matrix sum Test 1: FAILED\n");
   }

   freeMatrix(&C);

   changeEntry(B, 1,1,1);
   changeEntry(B, 1,2,0);
   changeEntry(B, 1,3,1);
   changeEntry(B, 2,1,0);
   changeEntry(B, 2,2,1);
   changeEntry(B, 2,3,0);
   changeEntry(B, 3,1,1);
   changeEntry(B, 3,2,1);
   changeEntry(B, 3,3,1);


   C = sum(A, B);
   if (NNZ(C) == 9) {
      printf("Matrix sum Test 2: PASSED\n");
   } else {
      printf("Matrix sum Test 2: FAILED\n");
   }

   printf("A+B: \n");
   printMatrix(stdout, C);

   freeMatrix(&C);


   printf("\n");
   printf("----------------TESTING diff()-------------------------\n");


   D = diff(A, A);

   if (NNZ(D) == 0) {
      printf("Matrix diff Test 1: PASSED\n");
   } else {
      printf("Matrix diff Test 1: FAILED\n");
   }

   freeMatrix(&D);

   D = diff(A, B);

   if (NNZ(D) == 8) {
      printf("Matrix diff Test 2: PASSED\n");
   } else {
      printf("Matrix diff Test 2: FAILED\n");
   }


   printf("A-B: \n");
   printMatrix(stdout, D);



   printf("\n");
   printf("----------------TESTING scalarMult()-------------------------\n");


   C = scalarMult(2, D);

   if (NNZ(C) == 8) {
      printf("Matrix scalarMult Test 1: PASSED\n");
   } else {
      printf("Matrix scalarMult Test 1: FAILED\n");
   }


   printf("2*(A-B): \n");
   printMatrix(stdout, C);

   freeMatrix(&C);


   printf("\n");
   printf("----------------TESTING product()-------------------------\n");

   C = product(B, B);


   if (NNZ(C) == 7) {
      printf("Matrix product Test 1: PASSED\n");
   } else {
      printf("Matrix product Test 1: FAILED\n");
   }

   freeMatrix(&C);

   changeEntry(B, 1, 1, 0);
   changeEntry(B, 2, 2, 0);

   C = product(B, B);

   if (NNZ(C) == 6) {
      printf("Matrix product Test 2: PASSED\n");
   } else {
      printf("Matrix product Test 2: FAILED\n");
   }


   printf("\n");
   printf("----------------TESTING equals()-------------------------\n");

   makeZero(A);
   makeZero(B);

   changeEntry(A, 1, 1, 1);
   changeEntry(A, 1, 2, 3);
   changeEntry(A, 1, 3, 4);

   changeEntry(B, 1, 1, 1);
   changeEntry(B, 1, 2, 3);
   changeEntry(B, 1, 3, 4);

   if (equals(A, B)) {
      printf("Matrix equals Test 1: PASSED\n");
   } else {
      printf("Matrix equals Test 1: FAILED\n");
   }

   changeEntry(B, 2, 3, 4);

   if (!equals(A, B)) {
      printf("Matrix equals Test 2: PASSED\n");
   } else {
      printf("Matrix equals Test 2: FAILED\n");
   }


   freeMatrix(&A);
   freeMatrix(&B);
   freeMatrix(&C);
   freeMatrix(&D);

   return EXIT_SUCCESS;
}

/*
----------------TESTING empty size and NNZ-------------------------
Matrix empty size Test: PASSED
Matrix empty NNZ Test: PASSED

----------------TESTING nonempty size and NNZ-------------------------
Matrix nonempty size Test: PASSED
Matrix nonempty NNZ Test: PASSED

----------------TESTING makeZero-------------------------
Matrix makeZero Test: PASSED

----------------TESTING changeEntry-------------------------
Matrix changeEntry Test 1: PASSED
Matrix changeEntry Test 2: PASSED

----------------TESTING copy()-------------------------
4
Matrix copy Test 1: PASSED
Matrix copy Test 2: PASSED

----------------TESTING transpose()-------------------------
Matrix transpose Test 1: PASSED

1: (1, 4.0)  (2, 2.0) 
4: (1, 8.0) 
5: (2, 3.0) 
6: (4, 9.0) 

1: (1, 4.0)  (4, 8.0) 
2: (1, 2.0)  (5, 3.0) 
4: (6, 9.0) 

----------------TESTING sum()-------------------------
Matrix sum Test 1: PASSED
Matrix sum Test 2: PASSED
A+B: 
1: (1, 2.0)  (2, 2.0)  (3, 4.0) 
2: (1, 4.0)  (2, 6.0)  (3, 6.0) 
3: (1, 8.0)  (2, 9.0)  (3, 10.0) 

----------------TESTING diff()-------------------------
Matrix diff Test 1: PASSED
Matrix diff Test 2: PASSED
A-B: 
1: (2, 2.0)  (3, 2.0) 
2: (1, 4.0)  (2, 4.0)  (3, 6.0) 
3: (1, 6.0)  (2, 7.0)  (3, 8.0) 

----------------TESTING scalarMult()-------------------------
Matrix scalarMult Test 1: PASSED
2*(A-B): 
1: (2, 4.0)  (3, 4.0) 
2: (1, 8.0)  (2, 8.0)  (3, 12.0) 
3: (1, 12.0)  (2, 14.0)  (3, 16.0) 

----------------TESTING product()-------------------------
Matrix product Test 1: PASSED
Matrix product Test 2: PASSED

----------------TESTING equals()-------------------------
Matrix equals Test 1: PASSED
Matrix equals Test 2: PASSED
*/