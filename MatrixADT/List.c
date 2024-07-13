/********************************************************************************* 
* Pav Sethi, pssethi
* 2023 Winter CSE101 PA #1
* List.c
*  Implementation file for Integer List ADT. Used Queue.c example
*********************************************************************************/ 

#include<stdio.h>
#include<stdlib.h>
#include<assert.h>
#include<stdbool.h>
#include "List.h"


// structs --------------------------------------------------------------------

// private Node type
typedef struct NodeObj* Node;

// private NodeObj type
typedef struct NodeObj{
   ListElement data;    //will track data value of new nodes 
   Node next;           // point to next node
   Node prev;           // point to previous node
} NodeObj;

// private ListObj type
typedef struct ListObj{
   Node front;          // tracks front element of list
   Node back;           // tracks back element of list
   Node cursor;         // will be used to traverse through list
   int length;          // tracks length of list
   int index;           // tracks which index cursor is at
} ListObj;


// Constructors-Destructors ---------------------------------------------------

// newNode()
// Returns reference to new Node object. Initializes next and data fields.
Node newNode(ListElement data){              // taken from Queue.c example
   Node N = malloc(sizeof(NodeObj));
   assert( N!=NULL );
   N->data = data;   
   N->next = NULL;
   N->prev = NULL;
   return(N);
}

// freeNode()
// Frees heap memory pointed to by *pN, sets *pN to NULL.
void freeNode(Node* pN){                     // taken from Queue.c example
   if( pN!=NULL && *pN!=NULL ){
      free(*pN);
      *pN = NULL;
   }
}

// newList()
// Creates and returns a new empty List.
List newList(void){                          // taken from Queue.c example
   List L = malloc(sizeof(ListObj));
   assert (L != NULL);
   L->front = L->back = NULL;
   L->length = 0;    
   L->cursor = NULL;
   L->index = -1;                            // cursor index will default to out of range of list/undefined

   return(L);
}


// freeList()
// Frees all heap memory associated with *pL, and sets *pL to NULL.
void freeList(List* pL)
{
   if (pL && *pL){
      clear(*pL);                            // first frees memory of each individual node in list and resets state of list
      free(*pL);                             // frees memory of entire list
      *pL = NULL;
   }
}


// Access functions -----------------------------------------------------------

// length()
// Returns the number of elements in L.
int length(List L)
{
   if( L==NULL ){
      printf("List Error: calling length() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   return(L->length);   
}

// index()
// Returns index of cursor element if defined, -1 otherwise.
int index(List L)
{
   if( L==NULL ){
      printf("List Error: calling index() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   return(L->index);
}

// front()
// Returns front element of L. Pre: length()>0
void* front(List L)
{
   if( L==NULL ){
      printf("List Error: calling front() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling front() on empty List\n");
      exit(EXIT_FAILURE);
   }
   return(L->front->data);
}

// back()
// Returns back element of L. Pre: length()>0
void* back(List L)
{
   if( L==NULL ){
      printf("List Error: calling back() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling back() on empty List\n");
      exit(EXIT_FAILURE);
   }
   return(L->back->data);
}

// get()
// Returns cursor element of L. Pre: length()>0, index()>=0
void* get(List L)
{
   if( L==NULL ){
      printf("List Error: calling get() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling get() on empty List\n");
      exit(EXIT_FAILURE);
   }
   if (index(L) < 0){
      printf("List Error: calling get() on List with index of cursor element off the list\n");
      exit(EXIT_FAILURE);
   }
   return(L->cursor->data);
}



// Manipulation procedures ----------------------------------------------------

// clear()
// Resets L to its original empty state.
void clear(List L)
{
   if (L) {                                                       // if L exists
      Node next = NULL;                                           // create Node to track the next node
      while (L->front != NULL){                                   // while the node being checked exists
         next = L->front->next;                                   // set the temp node to the next node
         freeNode(&L->front);                                     // free the front node
         L->front = next;                                         // set the front node to the temp which points to its next value for the next iteration
      }
      L->front = L->back = NULL;                                  // reset the state of L by setting all nodes back to NULL
      L->length = 0;                                              // reset length
      L->cursor = NULL;
      L->index = -1;                                              // reset index of cursor to undefined
   }
}

// set()
// Overwrites the cursor element’s data with x. Pre: length()>0, index()>=0
void set(List L, void* x)
{
   if( L==NULL ){
      printf("List Error: calling set() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling set() on empty List\n");
      exit(EXIT_FAILURE);
   }
   if (index(L) < 0){
      printf("List Error: calling set() on List with index of cursor element off the list\n");
      exit(EXIT_FAILURE);
   }
   L->cursor->data = x;                                           // setting cursors element to value of x
}


// moveFront()
// If L is non-empty, sets cursor under the front element, otherwise does nothing.
void moveFront(List L)
{
   if( L==NULL ){
      printf("List Error: calling set() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   L->cursor = L->front;                                          // move cursor to the front element
   if (L->cursor != NULL) {
      L->index = 0;                                                  // move cursor index to the index of 0 which is where first element is
   }
}


// moveBack()
// If L is non-empty, sets cursor under the back element, otherwise does nothing.
void moveBack(List L)
{
   if( L==NULL ){
      printf("List Error: calling set() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   L->cursor = L->back;                                           // move cursor to the back element
   L->index = L->length - 1;                                      // move cursor index to length - 1 because index starts at 0
}


// movePrev()
// If cursor is defined and not at front, move cursor one
// step toward the front of L; if cursor is defined and at
// front, cursor becomes undefined; if cursor is undefined
// do nothing
void movePrev(List L)
{
   if (L == NULL ){
      printf("List Error: calling movePrev() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (L->cursor != NULL && L->index != 0){
      L->cursor = L->cursor->prev;                                // if the cursor is defined and its not at the front then we can move it to its previous value
      L->index -= 1;                                              // decrement index of the cursor since it has been moved back one position
   } else if (L->cursor != NULL && L->index == 0){
      L->cursor = NULL;                                           // if the cursor is at the front then we can't move it back because there is no value there so set it to NULL
      L->index = -1;                                              // reset index to undefined
   }
}


// moveNext()
// If cursor is defined and not at back, move cursor one
// step toward the back of L; if cursor is defined and at
// back, cursor becomes undefined; if cursor is undefined
// do nothing
void moveNext(List L)
{
   if (L == NULL ){
      printf("List Error: calling moveNext() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (L->cursor != NULL && L->index != (L->length - 1)){         // if the cursor is defined and not at the back element
      L->cursor = L->cursor->next;                                // move the cursor to the value after it
      L->index += 1;                                              // increment index 
   } else if (L->cursor != NULL && L->index == (L->length - 1)){  // if the cursor is at the back element
      L->cursor = NULL;                                           // set cursor to NULL because no value exists after back element
      L->index = -1;                                              // reset index to undefined
   } 
}


// prepend()
// Insert new element into L. If L is non-empty,
// insertion takes place before front element.
void prepend(List L, void* x)
{
   if( L==NULL ){
      printf("List Error: calling insertBefore() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }

   Node new = newNode(x);                                         // node that will be inserted. has data value of input x
   if (L->length == 0) {                                          // if there are no elements in the list yet
      L->front = L->back = new;                                   // just set the new inserted node as the front and back node because it is the only one in the list now
      L->length += 1;                                             // increment length of list but index remains undefined until a move operation is called
   } else {                                                       // if there are elements in the list
      new->next = L->front;                                       // set the new nodes next to the front node
      new->prev = NULL;                                           // set the new nodes left to NULL since it is at the front now  
      L->front->prev = new;                                       // set the old fronts previous value to point to new node
      L->front = new;                                             // set front of list as the new node
      L->length += 1;                                             // increment length
   }
   if (L->index != -1){                                           // if the cursor is defined
      L->index += 1;                                              // increment the index since every element will get pushed forward one
   }
}


// append()
// Insert new element into L. If L is non-empty,
// insertion takes place after back element.
void append(List L, void* x)
{
   if (L){                                                        // if the List exists
      Node new = newNode(x);                                      // node that will be inserted. has data value of input x
      if (L->length == 0) {                                       // if there are no elements in the list yet
         L->front = L->back = new;                                // just set the new inserted node as the front and back node because it is the only one in the list now
         L->length += 1;                                          // increment length of list but index remains undefined until a move operation is called
      } else {                                                    // if there are elements in the list
         L->back->next = new;                                     // point the old backs next to the new node since it gets appended after back
         new->prev = L->back;                                     // set the new nodes previous to the old back
         L->back = new;                                           // set the back of the list as the new node
         L->length += 1;                                          // increment length but not index because cursor element will be before the insertion
      }
   } else {
      printf("List Error: calling append() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
}


// insertBefore()
// Insert new element before cursor.
// Pre: length()>0, index()>=0
void insertBefore(List L, void* x)
{
   if( L==NULL ){
      printf("List Error: calling insertBefore() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling insertBefore() on empty List\n");
      exit(EXIT_FAILURE);
   }
   if (index(L) < 0){
      printf("List Error: calling insertBefore() on List with index of cursor element off the list\n");
      exit(EXIT_FAILURE);
   }
   if (L->index == 0) {                                           // if the cursor is at the front of the list  
      prepend(L, x);                                              // we can call prepend because that already handles case of inserting before front element
   } else {
      Node new = newNode(x);                                      // new node to insert before cursor

      new->prev = L->cursor->prev;                                // set the new nodes previous to the cursors previous
      new->next = L->cursor;                                      // set the new nodes next to the cursor

      L->cursor->prev->next = new;                                // point the cursors previous's next to the new node
      L->cursor->prev = new;                                      // set the cursors previous to be the new node

      L->length += 1;                                             // increment length
      L->index += 1;                                              // increment index because everything is getting shifted right one 
   }
}


// insertAfter
// Insert new element after cursor.
// Pre: length()>0, index()>=0
void insertAfter(List L, void* x)
{
   if( L==NULL ){
      printf("List Error: calling insertAfter() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling insertAfter() on empty List\n");
      exit(EXIT_FAILURE);
   }
   if (index(L) < 0){
      printf("List Error: calling insertAfter() on List with index of cursor element off the list\n");
      exit(EXIT_FAILURE);
   }
   if (L->index == L->length - 1) {                               // if the cursor is at the back of the list
      append(L, x);                                               // we can call append because that already handles case of inserting after back element
   } else {
      Node new = newNode(x);                                      // new node to insert after cursor

      new->next = L->cursor->next;                                // set the new nodes next to the cursors next
      new->prev = L->cursor;                                      // set the new nodes previous to be the cursor

      L->cursor->next->prev = new;  
      L->cursor->next = new;                                      // set the cursors next to be the new node
                                                                  // point the cursors next previous to the new node

      L->length += 1;                                             // increment length but not index because insertion takes place after cursor index
   }
}


// deleteFront()
// Delete the front element. Pre: length()>0
void deleteFront(List L)
{
   if( L==NULL ){
      printf("List Error: calling deleteFront() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling deleteFront() on empty List\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 1) {                                          // if there is only one element in the list then just free the front node
      freeNode(&L->front);
      L->front = L->back = L->cursor = NULL;                      // reset all nodes to NULL
      L->length = 0;                                              // reset length
      L->index = -1;                                              // reset index 
   } else {
      Node deleteNode;                                            // front node that will be deleted
      deleteNode = L->front;
      L->front = L->front->next;                                  // first point the old node to its next value 
      freeNode(&deleteNode);                                      // delete the node that stores the front node
      L->front->prev = NULL;                                      // set the new front nodes previous to point to NULL and not to the old front
      if (L->index == 0) {                                        // if the cursor was at the front element then reset its state
         L->index = -1;
         L->cursor = NULL;
      } 
      L->length -= 1;                                             // decrement the length
      if (L->index != -1) {                                       // if the index is defined and not at the front element
         L->index -= 1;                                           // decrement index
      }  
   }
}


// deleteBack()
// Delete the back element. Pre: length()>0
void deleteBack(List L)
{
   if( L==NULL ){
      printf("List Error: calling deleteBack() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling deleteBack() on empty List\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 1) {
      deleteFront(L);                                             // if there is only one element in the list then call deleteFront which resets the state of list
   } else {
      Node prevNode;                                              // node to store the backs previous node which will become the new back node
      prevNode = L->back->prev;                                   // tutor Norton
      freeNode(&L->back);                                         // free the memory at the old back node
      L->back = prevNode;                                         // set the back node to its previous node
      L->back->next = NULL;                                       // set the new back nodes next to point to NULL and not the old back
      if (L->index == (L->length - 1)) {                          // if the cursor was at the back element
         L->index = -1;                                           // reset the cursor and its index
         L->cursor = NULL;
      }
      L->length -= 1;                                             // decrement length but not index
   }
}


// delete()
// Delete cursor element, making cursor undefined.
// Pre: length()>0, index()>=0
void delete(List L)
{
   if( L==NULL ){
      printf("List Error: calling delete() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }
   if (length(L) == 0){
      printf("List Error: calling delete() on empty List\n");
      exit(EXIT_FAILURE);
   }
   if (index(L) < 0){
      printf("List Error: calling delete() on List with index of cursor element off the list\n");
      exit(EXIT_FAILURE);
   }
   if (L->index == 0){                                            // if cursor is at the front then call deleteFront
      deleteFront(L);
   } else if (L->index == (L->length - 1)) {                      // else if cursor is at the back element then call deleteBack
      deleteBack(L);
   } else {
      Node tmpCursor;                                             // node to store the old cursor element
      tmpCursor = L->cursor;
      tmpCursor->prev->next = L->cursor->next;                    // point the cursors previous next to the cursors next
      tmpCursor->next->prev = L->cursor->prev;                    // point the cursors next previous to the cursors previous. These two actions break the link pointing to cursor
      freeNode(&L->cursor);                                       // free the memory at the cursor and set it to null
      L->length -= 1;                                             // decrement the length
      L->index = -1;                                              // cursor is undefined now so make its index undefined
   }
}


// Other operations -----------------------------------------------------------


// printList()
// Prints to the file pointed to by out, a
// string representation of L consisting
// of a space separated sequence of integers,
// with front on left.
// void printList(FILE* out, List L)                                 // taken from Queue.c
// {
//    Node N = NULL;

//    if( L==NULL ){
//       printf("List Error: calling printList() on NULL List reference\n");
//       exit(EXIT_FAILURE);
//    }

//    for(N = L->front; N != NULL; N = N->next){                     // loop from front of list until there are no more nodes
//       fprintf(out, "%d"" ", N->data);                             // print data at each node to out file
//    }  

// }




// Returns a new List which is the concatenation of
// A and B. The cursor in the new List is undefined,
// regardless of the states of the cursors in A and B.
// The states of A and B are unchanged.
List concatList(List A, List B)
{
   if( A==NULL || B == NULL){
      printf("List Error: calling concatList() on NULL List reference\n");
      exit(EXIT_FAILURE);
   }

   List concat = newList();                                     // list to store both list A and B

   Node C = NULL;

   for(C = A->front; C != NULL; C = C->next){                   // similar to copyList except will append both A and B list
      append(concat, C->data);
   }

   Node D = NULL;

   for (D = B->front; D != NULL; D = D->next) {
      append(concat, D->data);
   }

   return(concat);
}
