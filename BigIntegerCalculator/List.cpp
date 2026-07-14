#include<iostream>
#include<string>
#include<stdexcept>
#include"List.h"



// Private Constructor --------------------------------------------------------

// Node constructor
List::Node::Node(ListElement x){
   data = x;
   next = nullptr;
   prev = nullptr;
}


// Class Constructors & Destructors -------------------------------------------

// Creates a new List in the empty state.
List::List(){
   frontDummy = new Node(0);
   backDummy = new Node(0);
   frontDummy->next = backDummy;
   backDummy->prev = frontDummy;
   beforeCursor = frontDummy;
   afterCursor = backDummy;
   num_elements = 0;
   pos_cursor = 0;
}



// Copy constructor.
List::List(const List& L) {
   frontDummy = new Node(0);
   backDummy = new Node(0);
   frontDummy->next = backDummy;
   backDummy->prev = frontDummy;
   beforeCursor = frontDummy;
   afterCursor = backDummy;
   num_elements = 0;
   pos_cursor = 0;

   Node* N = L.frontDummy->next;
   while (N != L.backDummy) {
   		this->insertBefore(N->data);
   		N = N->next;
   }

}


// Destructor
List::~List(){
	moveFront();
	while(length() > 0){
		eraseAfter();
	}
	delete frontDummy;
	delete backDummy;

}


// Access functions --------------------------------------------------------

// length()
// Returns the length of this List.
int List::length() const
{
	return(num_elements);
}

// front()
// Returns the front element in this List.
// pre: length()>0
ListElement List::front() const
{
	if (length() == 0) {
		throw std::length_error("List: front(): empty List");
	}
	return(frontDummy->next->data);
}

// back()
// Returns the back element in this List.
// pre: length()>0
ListElement List::back() const
{
	if (length() == 0) {
		throw std::length_error("List: back(): empty List");
	}
	return(backDummy->prev->data);
}

// position()
// Returns the position of cursor in this List: 0 <= position() <= length().
int List::position() const
{
	if (pos_cursor < 0 || pos_cursor > length()){
		throw std::range_error("List: position(): invalid position of cursor");
	}
	return(pos_cursor);
}

// peekNext()
// Returns the element after the cursor.
// pre: position()<length()
ListElement List::peekNext() const
{
	if (position() >= length()) {
		throw std::range_error("List: peekNext(): cursor at back");
	}
	return(afterCursor->data);
}

// peekPrev()
// Returns the element before the cursor.
// pre: position()>0
ListElement List::peekPrev() const
{
	if (position() < 0) {
		throw std::range_error("List: peekPrev(): cursor at front");
	}
	return (beforeCursor->data);
}


// Manipulation procedures -------------------------------------------------

// clear()
// Deletes all elements in this List, setting it to the empty state.
void List::clear()
{
	moveFront();
	while(length() > 0){
		eraseAfter();
	}

}

// moveFront()
// Moves cursor to position 0 in this List.
void List::moveFront()
{
	beforeCursor = frontDummy;
	afterCursor = frontDummy->next;
	pos_cursor = 0;

	//printf("after: %d\n", afterCursor->data);

}

// moveBack()
// Moves cursor to position length() in this List.
void List::moveBack()
{
	afterCursor = backDummy;
	beforeCursor = backDummy->prev;
	pos_cursor = length();
}

// moveNext()
// Advances cursor to next higher position. Returns the List element that
// was passed over. 
// pre: position()<length() 
ListElement List::moveNext()
{
	if (position() >= length()) {
		throw std::range_error("List: moveNext(): cursor at back");
	}
	beforeCursor = afterCursor;
	afterCursor = afterCursor->next;
	pos_cursor += 1;
	return(beforeCursor->data);
} 

// movePrev()
// Advances cursor to next lower position. Returns the List element that
// was passed over. 
// pre: position()>0
ListElement List::movePrev()
{
	if (position() < 0) {
		throw std::range_error("List: movePrev(): cursor at front");
	}

	afterCursor = beforeCursor;
	beforeCursor = beforeCursor->prev;
	pos_cursor -= 1;
	return (afterCursor->data);
}

// insertAfter()
// Inserts x after cursor.
void List::insertAfter(ListElement x)
{
	Node* N = new Node(x);
 
	N->next = afterCursor;
	afterCursor->prev = N;
	N->prev = beforeCursor;
	beforeCursor->next = N;
	afterCursor = N;

	num_elements++;
}

// insertBefore()
// Inserts x before cursor.
void List::insertBefore(ListElement x)
{
	Node* N = new Node(x);

	N->prev = beforeCursor;
	beforeCursor->next = N;
	N->next = afterCursor;
	afterCursor->prev = N;
	beforeCursor = N;

	num_elements++;
	pos_cursor++;
}

// setAfter()
// Overwrites the List element after the cursor with x.
// pre: position()<length()
void List::setAfter(ListElement x)
{
	if (position() >= length()){
		throw std::range_error("List: setAfter(): cursor at back");
	}

	afterCursor->data = x;

}

// setBefore()
// Overwrites the List element before the cursor with x.
// pre: position()>0
void List::setBefore(ListElement x)
{
	if (position() < 0) {
		throw std::range_error("List: setBefore(): cursor at front");
	}

	beforeCursor->data = x;
}

// eraseAfter()
// Deletes element after cursor.
// pre: position()<length()
void List::eraseAfter()
{
	if (position() >= length()) {
		throw std::range_error("List: eraseAfter(): cursor at back");
	}
	Node* after = afterCursor;

	afterCursor = afterCursor->next;
	beforeCursor->next = afterCursor;
	afterCursor->prev = beforeCursor;

	num_elements--;
	delete after;
}

// eraseBefore()
// Deletes element before cursor.
// pre: position()>0
void List::eraseBefore()
{
	if (position() < 0) {
		throw std::range_error("List: eraseBefore(): cursor at front");
	}
	Node* before = beforeCursor;

	beforeCursor = beforeCursor->prev;
	afterCursor->prev = beforeCursor;
	beforeCursor->next = afterCursor;

	num_elements--;
	pos_cursor--;
	delete before;
}


// Other Functions ---------------------------------------------------------

// findNext()
// Starting from the current cursor position, performs a linear search (in 
// the direction front-to-back) for the first occurrence of element x. If x
// is found, places the cursor immediately after the found element, then 
// returns the final cursor position. If x is not found, places the cursor 
// at position length(), and returns -1. 
int List::findNext(ListElement x)
{
	if (beforeCursor->data == x) {
		moveNext();
	}
	//printf("cursor pos: %d\n", )
	for (int i = pos_cursor; i < length(); i++)
	{
		//printf("cursor pos: %d\n", beforeCursor->data);
		//printf("cursor pos: %d\n", afterCursor->data);
		if (beforeCursor->data == x){
			return i;
		}
		moveNext();
	}	
	pos_cursor = length();
	return -1;
}

// findPrev()
// Starting from the current cursor position, performs a linear search (in 
// the direction back-to-front) for the first occurrence of element x. If x
// is found, places the cursor immediately before the found element, then
// returns the final cursor position. If x is not found, places the cursor 
// at position 0, and returns -1. 
int List::findPrev(ListElement x)
{
	if (afterCursor->data == x) {
		movePrev();
	}

	for (int i = pos_cursor; i >= 0; i--)
	{
		if (afterCursor->data == x){
			return i;
		}
		movePrev();
	}	
	pos_cursor = 0;
	return -1;
}

// cleanup()
// Removes any repeated elements in this List, leaving only unique elements.
// The order of the remaining elements is obtained by retaining the frontmost 
// occurrance of each element, and removing all other occurances. The cursor 
// is not moved with respect to the retained elements, i.e. it lies between 
// the same two retained elements that it did before cleanup() was called.
void List::cleanup()
{
	Node* curr = frontDummy->next;

	while (curr != backDummy){
		int x = curr->data;
		Node* next = curr->next;
		while (next != backDummy) {
			if (next->data != x) {
				next = next->next;
			} else {
				if (next == beforeCursor) {
					next = next->next;
					eraseBefore(); 
				} else if (next == afterCursor) {
					next = next->next;
					eraseAfter();
				} else {
					Node* dup = next;
					next->prev->next = next->next;
					next->next->prev = next->prev;
					next = next->next;
					delete dup;
					num_elements--;
					if (pos_cursor >= length()) {
						pos_cursor--;
					}
					// next = next->next;
				}
				// next = next->next;
			}
		}
		curr = curr->next;
	}
}



// concat()
// Returns a new List consisting of the elements of this List, followed by
// the elements of L. The cursor in the returned List will be at postion 0.
List List::concat(const List& L) const
{
	List J;
	Node* N = this->frontDummy->next;
	Node* M = L.frontDummy->next;
	while( N!=this->backDummy ){
		J.insertBefore(N->data);
		N = N->next;
	}
	while( M!=L.backDummy ){
		J.insertBefore(M->data);
		M = M->next;
	}

	J.moveFront();
	return J;
}

// to_string()
// Returns a string representation of this List consisting of a comma 
// separated sequence of elements, surrounded by parentheses.
std::string List::to_string() const
{
   Node* N = nullptr;
   std::string s = "(";

   for(N=frontDummy->next; N!=backDummy; N=N->next){
   	  if (N == backDummy->prev) {
   	  	s += std::to_string(N->data);
   	  } else {
   	  	s += std::to_string(N->data)+", ";
   	  }
   }

   s += ")";
   
   return s;
}

// equals()
// Returns true if and only if this List is the same integer sequence as R.
// The cursors in this List and in R are unchanged.
bool List::equals(const List& R) const
{
	bool eq = false;
	Node* N = nullptr;
	Node* M = nullptr;

	//printf("hey\n");
	eq = ( this->num_elements == R.num_elements);
	//printf("hey\n");
	N = this->frontDummy->next;
	M = R.frontDummy->next;
	while( eq && N!=backDummy){
	//printf("N data: %d\n", N->data);
	//printf("M data: %d\n", M->data);
	  eq = (N->data==M->data);
	  N = N->next;
	  M = M->next;
	}
	return eq;
}

// Overriden Operators -----------------------------------------------------

// operator<<()
// Inserts string representation of L into stream.
std::ostream& operator<<( std::ostream& stream, const List& L )
{
	return stream << L.List::to_string();
}

// operator==()
// Returns true if and only if A is the same integer sequence as B. The 
// cursors in both Lists are unchanged.
bool operator==( const List& A, const List& B )
{
	return A.List::equals(B);
}

// operator=()
// Overwrites the state of this List with state of L.
List& List::operator=( const List& L )
{
	if( this != &L ){ // not self assignment
		// make a copy of Q
		List temp = L;


		// then swap the copy's fields with fields of this
		std::swap(frontDummy, temp.frontDummy);
		std::swap(backDummy, temp.backDummy);
		std::swap(beforeCursor, temp.beforeCursor);
		std::swap(afterCursor, temp.afterCursor);
		std::swap(pos_cursor, temp.pos_cursor);
		std::swap(num_elements, temp.num_elements);
	}

	// return this with the new data installed
	return *this;

	// // the copy, if there is one, is deleted upon return

}

