#include<iostream>
#include<string>
#include<stdexcept>
#include"BigInteger.h"

using namespace std;

int main(){

	BigInteger A;
	BigInteger B;
	BigInteger C;
	BigInteger D;

	cout << endl;

	cout << "----------------TESTING signs-------------------------" << endl;

	if (A.sign() == 0) {
	  cout << "sign Test 1: PASSED" << endl;
	} else {
	  cout << "sign Test 1: FAILED" << endl;
	}

	string s1 = "1234";
	string s2 = "-12345";
	string s3 = "+111234";

	A = BigInteger(s1);
	B = BigInteger(s2);
	C = BigInteger(s3);

	if (A.sign() == 1) {
	  cout << "sign Test 2: PASSED" << endl;
	} else {
	  cout << "sign Test 2: FAILED" << endl;
	}

	if (B.sign() == -1) {
	  cout << "sign Test 3: PASSED" << endl;
	} else {
	  cout << "sign Test 3: FAILED" << endl;
	}

	if (C.sign() == 1) {
	  cout << "sign Test 4: PASSED" << endl;
	} else {
	  cout << "sign Test 4: FAILED" << endl;
	}


	cout << endl;

	cout << "----------------TESTING makeZero-------------------------" << endl;

	A.makeZero();
	B.makeZero();

	if (A.sign() == 0) {
	  cout << "makeZero Test 1: PASSED" << endl;
	} else {
	  cout << "makeZero Test 1: FAILED" << endl;
	}

	if (B.sign() == 0) {
	  cout << "makeZero Test 2: PASSED" << endl;
	} else {
	  cout << "makeZero Test 2: FAILED" << endl;
	}

	cout << endl;

	cout << "----------------TESTING negate-------------------------" << endl;


	C.negate();

	if (C.sign() == -1) {
	  cout << "negate Test 1: PASSED" << endl;
	} else {
	  cout << "negate Test 1: FAILED" << endl;
	}


	A = BigInteger("+1234");

	if (A.sign() == 1) {
	  cout << "negate Test 2: PASSED" << endl;
	} else {
	  cout << "negate Test 2: FAILED" << endl;
	}


	cout << endl;

	cout << "----------------TESTING add-------------------------" << endl;

	A.makeZero();
	C.makeZero();
	B.makeZero();

	A = BigInteger("882133");
	B = BigInteger("659179");

	D = BigInteger("01541312");

	C = A + B;

	if (C == D) {
	  cout << "add Test 1: PASSED" << endl;
	} else {
	  cout << "add Test 1: FAILED" << endl;
	}

	A = BigInteger("1234");
	B = BigInteger("-1000");

	D = BigInteger("0234");

	C = A + B;

	if (C == D) {
	  cout << "add Test 2: PASSED" << endl;
	} else {
	  cout << "add Test 2: FAILED" << endl;
	}


	A = BigInteger("882133");
	B = BigInteger("659179");

	D = BigInteger("01541312");

	A += B;

	if (A == D) {
	  cout << "add Test 3: PASSED" << endl;
	} else {
	  cout << "add Test 3: FAILED" << endl;
	}


	cout << endl;

	cout << "----------------TESTING subtraction-------------------------" << endl;

	A.makeZero();
	C.makeZero();
	B.makeZero();
	D.makeZero();


	A = BigInteger("882133");
	B = BigInteger("659179");

	D = BigInteger("222954");

	C = A-B;

	if (C == D) {
	  cout << "subtraction Test 1: PASSED" << endl;
	} else {
	  cout << "subtraction Test 1: FAILED" << endl;
	}


	A = BigInteger("659179");
	B = BigInteger("882133");

	D = BigInteger("222954");

	C = A - B;

	if (C.sign() == -1) {
	  cout << "subtraction Test 2: PASSED" << endl;
	} else {
	  cout << "subtraction Test 2: FAILED" << endl;
	}

	if (C == D) {
	  cout << "subtraction Test 3: PASSED" << endl;
	} else {
	  cout << "subtraction Test 3: FAILED" << endl;
	}

	A = BigInteger("882133");
	B = BigInteger("659179");

	D = BigInteger("222954");

	A -= B;

	if (A == D) {
	  cout << "subtraction Test 4: PASSED" << endl;
	} else {
	  cout << "subtraction Test 4: FAILED" << endl;
	}


	cout << endl;

	cout << "----------------TESTING multiplication-------------------------" << endl;

	A.makeZero();
	C.makeZero();
	B.makeZero();
	D.makeZero();

	A = BigInteger("123");
	B = BigInteger("456");

	D = BigInteger("56088");


	C = A * B;

	if (C == D) {
	  cout << "multiplication Test 1: PASSED" << endl;
	} else {
	  cout << "multiplication Test 1: FAILED" << endl;
	}

	B.negate();
	D.negate();

	C = A * B;

	if (C == D) {
	  cout << "multiplication Test 2: PASSED" << endl;
	} else {
	  cout << "multiplication Test 2: FAILED" << endl;
	}


	A *= B;

	if (C == D) {
	  cout << "multiplication Test 3: PASSED" << endl;
	} else {
	  cout << "multiplication Test 3: FAILED" << endl;
	}


   cout << endl;

   return EXIT_SUCCESS;
}
