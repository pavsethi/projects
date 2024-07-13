/********************************************************************************* 
* Pav Sethi, pssethi
* 2023 Winter CSE101 PA #4
* Matrix.c
* Header file for Matrix ADT 
*********************************************************************************/ 

#include<stdio.h>
#include<stdlib.h>
#include<assert.h>
#include<stdbool.h>
#include "Matrix.h"
#include "List.h"



// structs --------------------------------------------------------------------

// private Entry type
typedef struct EntryObj* Entry;

// private EntryObj type
typedef struct EntryObj{
   int column;
   double value;
} EntryObj;

// private MatrixObj type
typedef struct MatrixObj{
   List *entries;
   int size;  
   int NNZ;                                           
} MatrixObj;



// Constructors-Destructors ---------------------------------------------------



// newEntry()
// Returns reference to new Entry object. Initializes fields.
Entry newEntry(int column, double value){              
   Entry E = malloc(sizeof(EntryObj));
   assert( E!=NULL );
   E->column = column;   
   E->value = value;
   return(E);
}

// freeEntry()
// Frees heap memory pointed to by *pE, sets *pE to NULL.
void freeEntry(Entry* pE)
{                     
   if( pE!=NULL && *pE!=NULL ){
      free(*pE);
      *pE = NULL;
   }
}

// newMatrix()
// Returns a reference to a new nXn Matrix object in the zero state.
Matrix newMatrix(int n)
{
	Matrix M = malloc(sizeof(MatrixObj));
	assert (M != NULL);
	M->size = n;
	M->NNZ = 0;
	M->entries = malloc((n+1) * sizeof(List));
	for (int i = 1; i <= n; i++) {
    	M->entries[i] = newList();																				//entries is a list of lists. each list is row in matrix
    }	
   return(M);
}


// freeMatrix()
// Frees heap memory associated with *pM, sets *pM to NULL.
void freeMatrix(Matrix* pM)
{
   if (pM && *pM) {
		for (int i = 1; i <= size(*pM); i ++) {	
			moveFront((*pM)->entries[i]);
			while (index((*pM)->entries[i]) != -1) {														//loop through each row in matrix			
				Entry E = (Entry)get((*pM)->entries[i]);													// get the entry in row. (col, val)
				freeEntry(&E);																						// free the entry
				moveNext((*pM)->entries[i]);																	// move on to next entry
			}
			freeList(&(*pM)->entries[i]);																		// free entire row
		}
		free((*pM)->entries);
      free(*pM);                            																 // frees memory of entire matrix
      *pM = NULL;
  }
}


// Access functions


// size()
// Return the size of square Matrix M.
int size(Matrix M)
{
   if( M==NULL ){
      printf("Matrix Error: calling size() on NULL Matrix reference\n");
      exit(EXIT_FAILURE);
   }
   return(M->size);   
}


// NNZ()
// Return the number of non-zero elements in M.
int NNZ(Matrix M)
{
   if( M==NULL ){
      printf("Matrix Error: calling NNZ() on NULL Matrix reference\n");
      exit(EXIT_FAILURE);
   }
   return(M->NNZ);   
}


// equals()
// Return true (1) if matrices A and B are equal, false (0) otherwise.
int equals(Matrix A, Matrix B)
{
   if( A==NULL || B == NULL ){
      printf("Matrix Error: calling equals() on NULL Matrix reference\n");
      exit(EXIT_FAILURE);
   }
   if (size(A) != size(B)){																							//return false if sizes aren't equal
   	return 0;
   }

	for (int i = 1; i <= size(A); i ++) {																			
		moveFront(A->entries[i]);
		moveFront(B->entries[i]);
		if (length(A->entries[i]) != length(B->entries[i])){												   // if lengths of row aren't equal, return false
   		return 0;
   	}
		while (index(A->entries[i]) != -1 && index(B->entries[i]) != -1) {								// loop while the index hasn't fallen off row
			if (((Entry)get(A->entries[i]))->value == ((Entry)get(B->entries[i]))->value){			// if the values in entry are equal then move on
				moveNext(A->entries[i]);
				moveNext(B->entries[i]);
			} else {
				return 0;																									//otherwise return false
			}
		}
	}
	return 1;
}


// Manipulation procedures


// makeZero()
// Re-sets M to the zero Matrix state.
void makeZero(Matrix M)
{
	if( M==NULL ){
	  printf("Matrix Error: calling makeZero() on NULL Matrix reference\n");
	  exit(EXIT_FAILURE);
	}

	for (int i = 1; i <= size(M); i ++) {
		moveFront(M->entries[i]);
		while (index(M->entries[i]) != -1) {
			Entry E = (Entry)get(M->entries[i]);
			freeEntry(&E);																								// loop through each row, and free the entry to make it 0
			moveNext(M->entries[i]);
		}
		clear(M->entries[i]);																						// clear the entire row
	}

	M->NNZ = 0;
}


// changeEntry()
// Changes the ith row, jth column of M to the value x.
// Pre: 1<=i<=size(M), 1<=j<=size(M)
void changeEntry(Matrix M, int i, int j, double x)
{
	if( M==NULL ){
	  printf("Matrix Error: calling makeZero() on NULL Matrix reference\n");
	  exit(EXIT_FAILURE);
	}
	if (i < 1 || i > size(M)) {
	  printf("Matrix Error: calling changeEntry() with invalid row\n");
	  exit(EXIT_FAILURE);
	}
	if (j < 1 || j > size(M)) {
	  printf("Matrix Error: calling changeEntry() with invalid column\n");
	  exit(EXIT_FAILURE);
	}

	if (length(M->entries[i]) == 0) {																			//if there aren't any entries in the row
		if (x != 0) {
			Entry val = newEntry(j, x);																			//create a new entry with x if it isn't 0
			prepend(M->entries[i], val);																			//add new entry to front of row
			M->NNZ += 1;																								//increment Non-Zero
			return;
		} else {
			return;																										//don't do anything if its 0
		}
	}

	moveFront(M->entries[i]);	
	while (index(M->entries[i]) != -1) {																	//loop through each entry in row
		if (((Entry)get(M->entries[i]))->column < j) {													//keep looping if haven't reached column
			moveNext(M->entries[i]);
		}
		else if (((Entry)get(M->entries[i]))->column == j) {											
			if (x != 0) {																							//if we are at column and x isn't 0
				((Entry)get(M->entries[i]))->value = x;													//set value at that entry to x
				M->NNZ += 1;
				return;
			} else {
				Entry getval = (Entry)get(M->entries[i]);													//if x is 0 and the column exists
				freeEntry(&getval);																				//free the entry and delete the node at column
				delete(M->entries[i]);
				M->NNZ -= 1;																						//decrement Non-zero
				return;
			}
		}
		else if (((Entry)get(M->entries[i]))->column > j) {											//if we went past the column because it doesn't exist
			if (x != 0) {
				Entry val = newEntry(j, x);																	//if x is not 0 then insert before your cursor
				insertBefore(M->entries[i], val);
				M->NNZ += 1;
				return;
			} else {
				return;				
			}	
		}
	}
	if (index(M->entries[i]) == -1) {																		//if index becomes -1 then it means column doesn't exist and it is at the end
		if (x != 0) {
			Entry val = newEntry(j, x);
			append(M->entries[i], val);																		//in this case we can just append entry to back of row
			M->NNZ += 1;
			return;
		} else {
			return;
		}
	}

}


// Matrix Arithmetic operations
// copy()
// Returns a reference to a new Matrix object having the same entries as A.
Matrix copy(Matrix A)
{
	if( A==NULL ){
	  printf("Matrix Error: calling copy() on NULL Matrix reference\n");
	  exit(EXIT_FAILURE);
	}

	Matrix C = newMatrix(size(A));


	for (int i = 1; i <= size(A); i ++) {
		moveFront(A->entries[i]);
		if (length(A->entries[i]) != 0) {	
   		while (index(A->entries[i]) != -1) {																// loop through the row
   			changeEntry(C, i, ((Entry)get(A->entries[i]))->column, ((Entry)get(A->entries[i]))->value);		//set the new matrix column and value to input matrix
   			moveNext(A->entries[i]);
   		}
		}
   }

   return (C);
}



// transpose()
// Returns a reference to a new Matrix object representing the transpose
// of A.
Matrix transpose(Matrix A)
{
	if( A==NULL ){
	  printf("Matrix Error: calling transpose() on NULL Matrix reference\n");
	  exit(EXIT_FAILURE);
	}

	Matrix T = newMatrix(size(A));

	for (int i = 1; i <= size(A); i ++) {
		moveFront(A->entries[i]);
		if (length(A->entries[i]) != 0) {
   		while (index(A->entries[i]) != -1) {
   			changeEntry(T, ((Entry)get(A->entries[i]))->column, i, ((Entry)get(A->entries[i]))->value);			//transpose swaps row and column
   			moveNext(A->entries[i]);
   		}
		}
   }

   return (T);

}


// scalarMult()
// Returns a reference to a new Matrix object representing xA.
Matrix scalarMult(double x, Matrix A)
{
	if( A==NULL ){
	  printf("Matrix Error: calling scalarMult() on NULL Matrix reference\n");
	  exit(EXIT_FAILURE);
	}


	Matrix sMult = newMatrix(size(A));

	for (int i = 1; i <= size(A); i ++) {
		moveFront(A->entries[i]);
		if (length(A->entries[i]) != 0) {
	   	while (index(A->entries[i]) != -1) {
	   		//printf("ypp\n");
				double mult = x * ((Entry)get(A->entries[i]))->value;
				changeEntry(sMult, i, ((Entry)get(A->entries[i]))->column, mult);										//set value at each entry to x*val
				moveNext(A->entries[i]);
			}
		}
   }

   return (sMult);

}


// sum()
// Returns a reference to a new Matrix object representing A+B.
// pre: size(A)==size(B)
Matrix sum(Matrix A, Matrix B)
{
   if( A==NULL || B == NULL ){
      printf("Matrix Error: calling sum() on NULL Matrix reference\n");
      exit(EXIT_FAILURE);
   }
   if (size(A) != size(B)) {
      printf("Matrix Error: calling sum() when size of Matrices don't match\n");
      exit(EXIT_FAILURE);
   }


   if (equals(A, B)) {																												//base case if matrices are equal then call scalarMult
   	return scalarMult(2, A);																									//otherwise cursor will move 2x fast and fall off too early
   } else {
   	Matrix sum = newMatrix(size(A));
		for (int i = 1; i <= size(A); i ++) {
			if (length(A->entries[i]) != 0 || length(B->entries[i]) != 0) {											//check that entries in at least 1 row
				moveFront(A->entries[i]);
				moveFront(B->entries[i]);
				while (index(A->entries[i]) != -1 && index(B->entries[i]) != -1) {									//loop while both indices are valid
					//printf("both index valid\n");
					Entry getA = ((Entry)get(A->entries[i]));
					Entry getB = ((Entry)get(B->entries[i]));

					if (getA->column == getB->column) {																			//if both columns exist, then add the values
						//printf("index valid and column same\n");
						changeEntry(sum, i, getA->column, getA->value + getB->value);
						moveNext(A->entries[i]);
						moveNext(B->entries[i]);
					} else if (getA->column > getB->column) {																	//if B's column is behind then add its value and let it catch up to A
						//printf("index valid and A > B \n");
						changeEntry(sum, i, getB->column, getB->value);
						moveNext(B->entries[i]);
					} else if (getA->column < getB->column){																	//if A's column is behind, then let A catch up
						//printf("index valid and A < B\n");	
						changeEntry(sum, i, getA->column, getA->value);
						moveNext(A->entries[i]);
					}
				}


				if (index(A->entries[i]) == -1){																					//if A index fell off meaning no more val in A row
					while (index(B->entries[i]) != -1) {
						//printf("A falls off\n");
						Entry getB = ((Entry)get(B->entries[i]));	
						//printf("yooooA\n");
						changeEntry(sum, i, getB->column, getB->value);														//only add rest of B's values of matrix
						moveNext(B->entries[i]);	
					}
				}
				if (index(B->entries[i]) == -1){																					//same logic as other if statement but add A's val
					while (index(A->entries[i]) != -1) {
						//printf("B falls off\n");
						Entry getA = ((Entry)get(A->entries[i]));
						//printf("yooooB\n");
						changeEntry(sum, i, getA->column, getA->value);
						moveNext(A->entries[i]);
					}
				}
			}
		}
		return (sum);
   }

}


// diff()
// Returns a reference to a new Matrix object representing A-B.
// pre: size(A)==size(B)
Matrix diff(Matrix A, Matrix B)
{
   if( A==NULL || B == NULL ){
      printf("Matrix Error: calling diff() on NULL Matrix reference\n");
      exit(EXIT_FAILURE);
   }
   if (size(A) != size(B)) {
      printf("Matrix Error: calling diff() when size of Matrices don't match\n");
      exit(EXIT_FAILURE);
   }


   Matrix diff = newMatrix(size(A));


	for (int i = 1; i <= size(A); i ++) {
		moveFront(A->entries[i]);
		moveFront(B->entries[i]);
		if (length(A->entries[i]) != 0 || length(B->entries[i]) != 0) {														//SAME LOGIC AS SUM
			while (index(A->entries[i]) != -1 && index(B->entries[i]) != -1) {
				Entry getA = ((Entry)get(A->entries[i]));
				Entry getB = ((Entry)get(B->entries[i]));

				if (getA->column == getB->column) {
					changeEntry(diff, i, getA->column, getA->value - getB->value);
					moveNext(A->entries[i]);
					moveNext(B->entries[i]);
				} else if (getA->column > getB->column) {
					changeEntry(diff, i, getB->column, -getB->value);
					moveNext(B->entries[i]);
				} else {
					changeEntry(diff, i, getA->column, getA->value);
					moveNext(A->entries[i]);
				}
			}

			if (index(A->entries[i]) == -1){
				while (index(B->entries[i]) != -1) {
					Entry getB = ((Entry)get(B->entries[i]));
					changeEntry(diff, i, getB->column, -getB->value);
					moveNext(B->entries[i]);
				}
			}
			if (index(B->entries[i]) == -1){
				while (index(A->entries[i]) != -1) {
					Entry getA = ((Entry)get(A->entries[i]));
					changeEntry(diff, i, getA->column, getA->value);
					moveNext(A->entries[i]);
				}
			}
		}
	}

	return (diff);

}



// vectorDot
// computes vector dot product of two matrix rows
double vectorDot(List P, List Q)																							//Helper function of product()
{	
   if( P==NULL || Q == NULL ){
      printf("List Error: calling vectorDot() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }

   double product = 0.0;

	moveFront(P);
	moveFront(Q);
	if (length(P) != 0 || length(Q) != 0) {
		while (index(P) != -1 && index(Q) != -1) {
			Entry getP = ((Entry)get(P));
			Entry getQ = ((Entry)get(Q));

			if (getP->column == getQ->column) {																			//similar to sum and diff, if both columns exist then multiply values
				product += getP->value * getQ->value;
				moveNext(P);
				moveNext(Q);
			} else if (getP->column > getQ->column) {																	//if Q is behind, don't add to product and let Q catch up
				moveNext(Q);
			} else {
				moveNext(P);																									//otherwise let P catch up
			}
		}
	}

	return (product);

}

// product()
// Returns a reference to a new Matrix object representing AB
// pre: size(A)==size(B)
Matrix product(Matrix A, Matrix B)
{
	if( A==NULL || B == NULL ){
	  printf("Matrix Error: calling diff() on NULL Matrix reference\n");
	  exit(EXIT_FAILURE);
	}
	if (size(A) != size(B)) {
	  printf("Matrix Error: calling diff() when size of Matrices don't match\n");
	  exit(EXIT_FAILURE);
	}

	Matrix prod = newMatrix(size(A));
	Matrix T = transpose(B);																							//transpose B matrix so we can multiply row by row

  	for (int i = 1; i <= size(A); i ++) {																			//loop through row
		for (int j = 1; j <= size(A); j ++) {																	//loop through column
			if (length(A->entries[i]) != 0 && length(T->entries[j]) != 0) {							
				moveFront(A->entries[i]);
				moveFront(T->entries[j]);
				double product = vectorDot(A->entries[i], T->entries[j]);								//call vector dot on A row and each row of T which is columns since it is transpose
				changeEntry(prod, i, j, product);
			}
		}
   }
   freeMatrix(&T);																										//free the transpose matrix
   return (prod);

}


// printMatrix()
// Prints a string representation of Matrix M to filestream out. Zero rows
// are not printed. Each non-zero row is represented as one line consisting
// of the row number, followed by a colon, a space, then a space separated
// list of pairs "(col, val)" giving the column numbers and non-zero values
// in that row. The double val will be rounded to 1 decimal point.
void printMatrix(FILE* out, Matrix M)
{
   if( M==NULL ){
      printf("Matrix Error: calling printMatrix() on NULL Matrix reference\n");
      exit(EXIT_FAILURE);
   }

   for (int i = 1; i <= size(M); i++) {																		//taken from printGraph
      if (length(M->entries[i]) != 0) {
      	fprintf(out, "%d:", i);
         for (moveFront(M->entries[i]); index(M->entries[i]) != -1; moveNext(M->entries[i])){
         	double getVal = ((Entry)get(M->entries[i]))->value;
         	int getCol = ((Entry)get(M->entries[i]))->column;
            fprintf(out, " (%d, %0.1f) ", getCol, getVal);
         }
         fprintf(out, "\n");
      } 
   }
}



