/********************************************************************************* 
* Pav Sethi, pssethi
* 2023 Winter CSE101 PA #1
* ListTest.c
* Tests each individual function for Integer List ADT 
*********************************************************************************/ 

#include<stdio.h>
#include<stdlib.h>
#include<stdbool.h>
#include"List.h"

int main(int argc, char* argv[]){

   List A = newList();
   List B = newList();
   double i;


   printf("----------------TESTING APPEND AND PREPEND-------------------------\n");
   for(i=1; i<=20.0; i++){
      append(A,i);
      prepend(B,i);
   }

   printf("----------------A is list made with Append-------------------------\n");
   printList(stdout,A); 
   printf("\n");

   printf("----------------B is list made with Prepend-------------------------\n");
   printList(stdout,B); 
   printf("\n");

   printf("----------------Testing Length of A and B-------------------------\n");

   if (length(A) == 20) {
      printf("A Length Test: PASSED\n");
   } else {
      printf("A Length Test: FAILED\n");
   }

   if (length(B) == 20) {
      printf("B Length Test: PASSED\n");
   } else {
      printf("B Length Test: FAILED\n");
   }

   printf("----------------Testing Index of A and B with moveFront and moveNext-------------------------\n");

   moveFront(A);
   if (index(A) == 0) {
      printf("A moveFront Index Test: PASSED\n");
   } else {
      printf("A moveFront Index Test: FAILED\n");
   }

   moveFront(B);
   if (index(B) == 0) {
      printf("B moveFront Index Test: PASSED\n");
   } else {
      printf("B moveFront Index Test: FAILED\n");
   }

   moveNext(A);
   moveNext(A);

   if (index(A) == 2) {
      printf("A moveNext Index Test: PASSED\n");
   } else {
      printf("A moveNext Index Test: FAILED\n");
   }

   moveNext(B);
   moveNext(B);

   if (index(B) == 2) {
      printf("B moveNext Index Test: PASSED\n");
   } else {
      printf("B moveNext Index Test: FAILED\n");
   }



   printf("----------------Testing Index of A and B with moveBack and movePrev-------------------------\n");

   moveBack(A);
   if (index(A) == length(A) - 1) {
      printf("A moveBack Index Test: PASSED\n");
   } else {
      printf("A moveBack Index Test: FAILED\n");
   }

   moveBack(B);
   if (index(B) == length(A) - 1) {
      printf("B moveBack Index Test: PASSED\n");
   } else {
      printf("B moveBack Index Test: FAILED\n");
   }

   movePrev(A);
   movePrev(A);

   if (index(A) == 17) {
      printf("A movePrev Index Test: PASSED\n");
   } else {
      printf("A movePrev Index Test: FAILED\n");
   }

   movePrev(B);
   movePrev(B);

   if (index(B) == 17) {
      printf("B movePrev Index Test: PASSED\n");
   } else {
      printf("B movePrev Index Test: FAILED\n");
   }

   printf("----------------Testing Index of A and B with moveFront and movePrev-------------------------\n");

   moveFront(A);
   movePrev(A);
   if (index(A) == -1) {
      printf("A moveFront and movePrev Index Test: PASSED\n");
   } else {
      printf("A moveFront and movePrev Index Test: FAILED\n");
   }

   moveFront(B);
   movePrev(B);
   if (index(B) == -1) {
      printf("B moveFront and movePrev Index Test: PASSED\n");
   } else {
      printf("B moveFront and movePrev Index Test: FAILED\n");
   }

   printf("----------------Testing Front and Back of A and B-------------------------\n");

   if (front(A) == 1) {
      printf("A front() Test: PASSED\n");
   } else {
      printf("A front(): FAILED\n");
   }

   if (front(B) == 20) {
      printf("B front() Test: PASSED\n");
   } else {
      printf("B front(): FAILED\n");
   }

   if (back(A) == 20) {
      printf("A back() Test: PASSED\n");
   } else {
      printf("A back(): FAILED\n");
   }

   if (back(B) == 1) {
      printf("B back() Test: PASSED\n");
   } else {
      printf("B back(): FAILED\n");
   }

   // TESTING IF A AND B ARE EQUAL
   printf("Testing A and B equality:  %s\n", equals(A,B)?"true":"false");

   printf("----------------Testing set() and get() of A and B-------------------------\n");

   moveFront(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);

   set(A, 29);

   if (get(A) == 29) {
      printf("A get() and set() Test: PASSED\n");
   } else {
      printf("A get() and set(): FAILED\n");
   }

   printf("New A list with set value: \n");
   printList(stdout, A);
   printf("\n");


   printf("----------------Testing insertBefore() of A-------------------------\n");

   printf("Inserting before at front of List: \n");

   moveFront(A);
   insertBefore(A, 64);

   if (front(A) == 64) {
      printf("A insertBefore() test: PASSED\n");
   } else {
      printf("A insertBefore() test: FAILED\n");
   }

   printf("New A list with 64 inserted before front of list: \n");
   printList(stdout, A);
   printf("\n");


   printf("Inserting before at random index of List: \n");

   moveFront(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);

   insertBefore(A, 102);

   printf("New A list with 102 inserted at index 7 of list: \n");
   printList(stdout, A);
   printf("\n");


   printf("----------------Testing insertAfter() of A-------------------------\n");

   printf("Inserting after at end of List: \n");

   moveBack(A);
   insertAfter(A, 100);

   if (back(A) == 100) {
      printf("A insertAfter() test: PASSED");
   } else {
      printf("A insertAfter() test: FAILED");
   }

   printf("New A list with 100 inserted after back of list: \n");
   printList(stdout, A);
   printf("\n");


   printf("Inserting after at random index of List: \n");

   moveFront(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);
   moveNext(A);

   insertBefore(A, 130);

   printf("New A list with 130 inserted before at index 8 of list: \n");
   printList(stdout, A);
   printf("\n");


 
   printf("----------------Testing deleteFront() of List with Length 1-------------------------\n");

   List C = newList();

   append(C, 4);

   printf("New C list with 1 element: \n");
   printList(stdout, C);
   printf("\n");

   deleteFront(C);

   printf("C list with 1 element and deletFront(): \n");
   printList(stdout, C);
   printf("\n");

   if (length(C) == 0 && index(C) == -1) {
      printf("deleteFront() on list with 1 element: PASSED\n");
   } else {
      printf("deleteFront() on list with 1 element: FAILED\n");
   }




   printf("----------------Testing deleteFront() of List A with more than 1 element-------------------------\n");

   printf("Old A list before deleteFront(): \n");
   printList(stdout, A);
   printf("\n");

   deleteFront(A);

   printf("A list with deletFront(): \n");
   printList(stdout, A);
   printf("\n");

   printf("deleteFront() on list A: PASSED\n");


   printf("----------------Testing deleteBack() of List with Length 1-------------------------\n");

   List D = newList();

   append(D, 9);

   printf("New D list with 1 element: \n");
   printList(stdout, D);
   printf("\n");

   deleteBack(D);

   printf("D list with 1 element and deleteBack(): \n");
   printList(stdout, D);
   printf("\n");

   if (length(D) == 0 && index(D) == -1) {
      printf("deleteBack() on list with 1 element: PASSED\n");
   } else {
      printf("deleteBack() on list with 1 element: FAILED\n");
   }




   printf("----------------Testing deleteBack() of List B with more than 1 element-------------------------\n");

   printf("Old B list before deleteBack(): \n");
   printList(stdout, B);
   printf("\n");

   deleteBack(B);

   printf("B list with deletBack(): \n");
   printList(stdout, B);
   printf("\n");

   printf("deleteBack() on list B: PASSED\n");



   printf("----------------Testing delete() of List with Length 1-------------------------\n");

   List E = newList();

   append(E, 10);

   printf("New E list with 1 element: \n");
   printList(stdout, E);
   printf("\n");

   deleteBack(E);

   printf("E list with 1 element and delete(): \n");
   printList(stdout, E);
   printf("\n");

   if (length(D) == 0 && index(D) == -1) {
      printf("delete() on list with 1 element: PASSED\n");
   } else {
      printf("delete() on list with 1 element: FAILED\n");
   }


   printf("----------------Testing delete() of List A with more than 1 element-------------------------\n");

   printf("Old A list before delete(): \n");
   printList(stdout, A);
   printf("\n");

   delete(A);

   printf("A list with delete(): \n");
   printList(stdout, A);
   printf("\n");

   printf("delete() on list A: PASSED\n");


   printf("----------------Testing concatList()-------------------------\n");

   List F = newList();
   F = concatList(A, B);


   printList(stdout, F);
   printf("\n");



   freeList(&A);
   freeList(&B);
   freeList(&C);
   freeList(&D);
   freeList(&E);

   return(0);
}

/*
Output of this program:


----------------TESTING APPEND AND PREPEND-------------------------
----------------A is list made with Append-------------------------
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 
----------------B is list made with Prepend-------------------------
20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 
----------------Testing Length of A and B-------------------------
A Length Test: PASSED
B Length Test: PASSED
----------------Testing Index of A and B with moveFront and moveNext-------------------------
A moveFront Index Test: PASSED
B moveFront Index Test: PASSED
A moveNext Index Test: PASSED
B moveNext Index Test: PASSED
----------------Testing Index of A and B with moveBack and movePrev-------------------------
A moveBack Index Test: PASSED
B moveBack Index Test: PASSED
A movePrev Index Test: PASSED
B movePrev Index Test: PASSED
----------------Testing Index of A and B with moveFront and movePrev-------------------------
A moveFront and movePrev Index Test: PASSED
B moveFront and movePrev Index Test: PASSED
----------------Testing Front and Back of A and B-------------------------
A front() Test: PASSED
B front() Test: PASSED
A back() Test: PASSED
B back() Test: PASSED
Testing A and B equality:  false
----------------Testing set() and get() of A and B-------------------------
A get() and set() Test: PASSED
New A list with set value: 
1 2 3 29 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 
----------------Testing insertBefore() of A-------------------------
Inserting before at front of List: 
A insertBefore() test: PASSED
New A list with 64 inserted before front of list: 
64 1 2 3 29 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 
Inserting before at random index of List: 
New A list with 102 inserted at index 7 of list: 
64 1 2 3 29 5 102 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 
----------------Testing insertAfter() of A-------------------------
Inserting after at end of List: 
A insertAfter() test: PASSEDNew A list with 100 inserted after back of list: 
64 1 2 3 29 5 102 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 100 
Inserting after at random index of List: 
New A list with 130 inserted before at index 8 of list: 
64 1 2 3 29 5 102 130 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 100 
----------------Testing deleteFront() of List with Length 1-------------------------
New C list with 1 element: 
4 
C list with 1 element and deletFront(): 

deleteFront() on list with 1 element: PASSED
----------------Testing deleteFront() of List A with more than 1 element-------------------------
Old A list before deleteFront(): 
64 1 2 3 29 5 102 130 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 100 
A list with deletFront(): 
1 2 3 29 5 102 130 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 100 
deleteFront() on list A: PASSED
----------------Testing deleteBack() of List with Length 1-------------------------
New D list with 1 element: 
9 
D list with 1 element and deleteBack(): 

deleteBack() on list with 1 element: PASSED
----------------Testing deleteBack() of List B with more than 1 element-------------------------
Old B list before deleteBack(): 
20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 
B list with deletBack(): 
20 19 18 17 16 15 14 13 12 11 10 9 8 7 6 5 4 3 2 
deleteBack() on list B: PASSED
----------------Testing delete() of List with Length 1-------------------------
New E list with 1 element: 
10 
E list with 1 element and delete(): 

delete() on list with 1 element: PASSED
----------------Testing delete() of List A with more than 1 element-------------------------
Old A list before delete(): 
1 2 3 29 5 102 130 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 100 
A list with delete(): 
1 2 3 29 5 102 130 7 8 9 10 11 12 13 14 15 16 17 18 19 20 100 
delete() on list A: PASSED
*/