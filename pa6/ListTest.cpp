/********************************************************************************* 
* Pav Sethi, pssethi
* 2023 Winter CSE101 PA #5
* ListTest.c
* Tests each individual function for List ADT 
*********************************************************************************/ 
#include<iostream>
#include<string>
#include<stdexcept>
#include"List.h"
#include "BigInteger.h"

using namespace std;


int main() {

	List A;
	List B;
	
	cout << endl;

	cout << "----------------TESTING insertAfter and insertBefore-------------------------" << endl;

	for(int i=1; i<= 10; i++){
		A.insertAfter(i);
		B.insertBefore(i);
	}

	cout << "----------------A is list made with insertAfter-------------------------" << endl;
	cout << "A = " << A << endl;


	cout << "----------------B is list made with insertBefore-------------------------" << endl;
	cout << "B = " << B << endl;

	cout << "----------------Testing Length of A and B-------------------------" << endl;

	if (A.length() == 10) {
	  cout << "A length Test: PASSED" << endl;
	} else {
	  cout << "A length Test: FAILED" << endl;
	}

	if (B.length() == 10) {
	  cout << "B length Test: PASSED" << endl;
	} else {
	  cout << "B length Test: FAILED" << endl;
	}

	cout << "----------------Testing moveFront and moveBack-------------------------" << endl;

	A.moveFront();
	cout << "A.position() after moveFront: " << A.position() << endl;

	B.moveBack();
	cout << "B.position() after moveBack: " << B.position() << endl;

	if (A.position() == 0) {
	  cout << "A moveFront position Test: PASSED" << endl;
	} else {
	  cout << "A moveFront position Test: FAILED" << endl;
	}

	if (B.position() == 10) {
	  cout << "B moveBack position Test: PASSED" << endl;
	} else {
	  cout << "B moveBack position Test: FAILED" << endl;
	}


	cout << "----------------Testing moveNext-------------------------" << endl;

	for (int i = 0; i < 7; i++) {
		cout<< A.moveNext() << " ";
	}

	cout << endl;

	cout << "A.moveNext() position: " << A.position() << endl;

	if (A.position() == 7) {
	  cout << "A moveNext position Test: PASSED" << endl;
	} else {
	  cout << "A moveNext position Test: FAILED" << endl;
	}


	cout << "----------------Testing movePrev-------------------------" << endl;

	for (int i = 0; i < 7; i++) {
		cout<< B.movePrev() << " ";
	}

	cout << endl;

	cout << "B.movePrev() position: " << B.position() << endl;

	if (B.position() == 3) {
	  cout << "B movePrev position Test: PASSED" << endl;
	} else {
	  cout << "B movePrev position Test: FAILED" << endl;
	}


	cout << "----------------Testing peekNext and peekPrev-------------------------" << endl;


	if (A.peekNext() == 3) {
		cout << "A peekNext() Test: PASSED" << endl;
	} else {
	   cout << "A peekNext() Test: FAILED" << endl;
	}

	if (A.peekPrev() == 4){
		cout << "A peekPrev() Test: PASSED" << endl;
	} else {
	   cout << "A peekPrev() Test: FAILED" << endl;
	}

	if (B.peekNext() == 4) {
		cout << "B peekNext() Test: PASSED" << endl;
	} else {
	   cout << "B peekNext() Test: FAILED" << endl;
	}

	if (B.peekPrev() == 3){
		cout << "B peekPrev() Test: PASSED" << endl;
	} else {
	   cout << "B peekPrev() Test: FAILED" << endl;
	}


	cout << "----------------Testing setAfter and setBefore-------------------------" << endl;

	A.setAfter(24);

	cout << "A = " << A << endl;

	if (A.peekNext() == 24) {
		cout << "A setAfter Test: PASSED" << endl;
	} else {
	   cout << "A setAfter Test: FAILED" << endl;
	}

	B.setBefore(33);

	cout << "B = " << B << endl;

	if (B.peekPrev() == 33) {
		cout << "B setBefore Test: PASSED" << endl;
	} else {
	   cout << "B setBefore Test: FAILED" << endl;
	}


	cout << "----------------Testing eraseAfter and eraseBefore-------------------------" << endl;

	A.eraseBefore();
	cout << "A = " << A << endl;

	B.eraseAfter();
	cout << "B = " << B << endl;

	cout << "----------------Testing findNext and findPrev-------------------------" << endl;

	A.moveFront();
	B.moveBack();

	A.findNext(5);
	if (A.position() == 6) {
		cout << "A findNext Test: PASSED" << endl;
	} else {
	   cout << "A findNext Test: FAILED" << endl;
	}

	B.findPrev(2);
	if (B.position() == 1) {
		cout << "B findPrev Test: PASSED" << endl;
	} else {
	   cout << "B findPrev Test: FAILED" << endl;
	}

	cout << "B invalid findPrev: " << B.findPrev(11) << endl;


	cout << "----------------Testing cleanup()-------------------------" << endl;

	A.moveBack();
	for(int i=10; i>=1; i--){
		A.insertAfter(i);
		A.movePrev();
	}

	cout << "A = " << A << endl;

	A.moveBack();
	cout << "A position: " << A.position() << endl;

	A.cleanup();

	cout << "A = " << A << endl;

	cout << "A position after cleanup: " << A.position() << endl;


	cout << "----------------Testing concat()-------------------------" << endl;

	List C = A.concat(B);

	cout << "Concat List: " << C << endl;

	cout << "----------------Testing equals()-------------------------" << endl;

	cout << "A==B is " << (A==B?"true":"false") << endl;



}