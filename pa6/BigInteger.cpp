/********************************************************************************* 
* Pav Sethi, pssethi
* 2023 Winter CSE101 PA #6
* BigInteger.cpp
* Implementation of BigInteger ADT 
*********************************************************************************/ 

#include<iostream>
#include<string>
#include<stdexcept>
#include <sstream>
#include <iomanip>
#include"BigInteger.h"


#define BASE 1000000000
#define POWER 9

using namespace std;


// Helper Functions

// negateList()
// Changes the sign of each integer in List L. Used by sub().
void negateList(List& L)
{
	L.moveBack();
	while (L.position() > 0) {
		ListElement x = L.movePrev();
		if (x == 0) {
			continue;
		}
		L.setAfter((-1) * x);
	}
}


// sumList()
// Overwrites the state of S with A + sgn*B (considered as vectors).
// Used by both sum() and sub().
void sumList(List& S, List A, List B, int sgn)				
{
	S.clear();
	S.moveBack();
	A.moveBack();
	B.moveBack();


	while (A.position() > 0 && B.position() > 0) {
		ListElement a = A.movePrev();
		//cout << "A: " << a << endl;
		ListElement b = B.movePrev();
		//cout << "B: " << b << endl;
		S.insertAfter(a + (sgn*b));
		//cout << "S: " << S << endl;
	}
	while (A.position() > 0 ) {
		ListElement a = A.movePrev();
		S.insertAfter(a);
	}
	while (B.position() > 0) {
		ListElement b = B.movePrev();
		S.insertAfter(sgn*b);
	}

	S.moveFront();
	while (S.moveNext() == 0 && S.position() < S.length()) {
		S.eraseBefore();
	}
}


// normalizeList()
// Performs carries from right to left (least to most significant
// digits), then returns the sign of the resulting integer. Used
// by add(), sub() and mult().
int normalizeList(List& L)				//TA Baswati
{
	L.moveBack();
	long carry = 0;
	long remain = 0;
	while (L.position() > 0) {
		//cout << L << endl;
		ListElement val = L.movePrev();
		if (val < 0) {
			carry = 
			;
		} else {
			carry = val / BASE;
		}
		//cout << "val = " << val << endl;
		//cout << "c = " << carry << endl;
		//cout << "p = " << L.position() << endl;
		remain = val % BASE;
		//cout << "r = " << remain << endl;
		if (remain < 0 && L.position() != 0) {
			L.setAfter(L.peekNext() + BASE);
		} else {
			L.setAfter(remain);
		}

		// cout << "peekPrev: " << L.peekPrev() << endl;
		L.setBefore(L.peekPrev() + carry);
		//cout << "peekNext: " << L.peekNext() << endl;
		//cout << "peekPrev: " << L.peekPrev() << endl;
	}

	if (carry > 0) {
		L.insertBefore(carry);
	}

	//cout << "before Check Again: " << L << endl;
	L.moveFront();
	int sign = 0;
	if (L.length() != 0) {
		if (L.moveNext() < 0) {
			sign = -1;
			//cout << "before Negate : " << L << endl;
			negateList(L);
			//cout << "After Negate Again: " << L << endl;
			//cout << "before Norm Again: " << L << endl;
			normalizeList(L);
		} else {
			sign = 1;
		}
	} else {
		sign = 0;
	}

	return sign;
}


// shiftList()
// Prepends p zero digits to L, multiplying L by base^p. Used by mult().
void shiftList(List& L, int p)
{
	L.moveBack();
	for (int i = 0; i < p; i++) {
		L.insertBefore(0);
	}
}


// scalarMultList()
// Multiplies L (considered as a vector) by 
void scalarMultList(List& L, ListElement m)
{
	L.moveFront();
	while (L.position() < L.length()) {
		ListElement x = L.moveNext();
		if (x == 0) {
			continue;
		} else {
			L.setBefore(x * m);
		}
	}
}


// Class Constructors & Destructors -------------------------------------------



BigInteger::BigInteger()
{
	signum = 0;
	digits = List();
}

// BigInteger()
// Constructor that creates a new BigInteger from the string s.
// Pre: s is a non-empty string consisting of (at least one) base 10 digit
// {0,1,2,3,4,5,6,7,8,9}, and an optional sign {+,-} prefix.
BigInteger::BigInteger(std::string s)
{

	if (s.length() == 0) {
		throw std::invalid_argument("BigInteger: Constructor: empty string");
	}

	int n = s.length();

	if (s[0] == '-') {
		signum = -1;
		s.erase(0,1);
		n--;
	} else if (s[0] == '+') {
		signum = 1;
		s.erase(0,1);
		n--;
	} else{
		signum = 1;
	}

	while (n > 1 && s[0] == '0') {				// TA Mike Psuedocode --> erasing all leading 0's so I don't write them to the list of digits
		s.erase(0,1);
		n--;
	}
	if (n == 1 && s[0] == '0') {
		signum = 0;
	}


	digits = List();

	int counter = 0; 
	string d; 
	long x;
	for (int i = n-1; i >= 0; i--) {
		// printf("s[i]: %c\n" , s[i]);
		// printf("c: %d\n" , counter);
		//cout << "d:" << d << endl;
		if (isdigit(s[i]) == 0){
			throw std::invalid_argument("BigInteger: Constructor: non-numeric string");
		}
		if (counter != POWER) {
			d = s[i] + d;  
			//printf("%c\n" , s[i]);
			counter++;
			//continue; //i added this so it dont insertAfter in the list every iteration 
		}
		if (counter == POWER) {
			x = stol(d);
			d = "";
			digits.insertAfter(x); 
			counter = 0;
		}
	}

	if (d.length() != 0) {
		x = stol(d);
		digits.insertAfter(x);
	}

	//cout << digits << endl;
}

// BigInteger()
// Constructor that creates a copy of N.
BigInteger::BigInteger(const BigInteger& N)
{
	this->signum = N.signum;
	this->digits = N.digits;

}


// Access functions --------------------------------------------------------

// sign()
// Returns -1, 1 or 0 according to whether this BigInteger is negative, 
// positive or 0, respectively.
int BigInteger::sign() const
{
	return signum;
}

// compare()
// Returns -1, 1 or 0 according to whether this BigInteger is less than N,
// greater than N or equal to N, respectively.
int BigInteger::compare(const BigInteger& N) const
{
	//int cmp;
	List L = this->digits;
	List R = N.digits;

	if (this->signum > N.signum) {
		//cmp = 1;
		return 1;
	}
	if (L.length() < R.length()){
		//cmp = -1;
		return -1;
	}

	L.moveFront();
	R.moveFront();

	while (L.position() < L.length() && R.position() < R.length()) {
		ListElement l = L.moveNext();
		ListElement r = R.moveNext();

		//cout << "l: " << l << endl;
		//cout << "r: " << r << endl;

		if (l < r){
			//cmp = -1;
			return -1;
		} else if (l > r) {
			//cmp = 1;
			return 1;
		} else {
			//cmp = 0;
			continue;
		}

		//cout << "cmp: " << cmp << endl;
	}

	//cout << "cmp: " << cmp << endl;
	return 0;
}


// Manipulation procedures -------------------------------------------------

// makeZero()
// Re-sets this BigInteger to the zero state.
void BigInteger::makeZero()
{
	digits.clear();
	signum = 0;
}

// negate()
// If this BigInteger is zero, does nothing, otherwise reverses the sign of 
// this BigInteger positive <--> negative. 
void BigInteger::negate(){
	if (signum == 0) {
		return;
	}
	signum = -signum;
}


// BigInteger Arithmetic operations ----------------------------------------

// add()
// Returns a BigInteger representing the sum of this and N.
BigInteger BigInteger::add(const BigInteger& N) const							// TA Mike Psuedo
{
	BigInteger Sum;
	int sign; 
	//int sgn = 1;

	List A = this->digits;
	List B = N.digits;
	List &S = Sum.digits;

	if (this->signum == N.signum) {
		sign = 1;
		sumList(S, A, B, sign);
		//cout << "SumList = " << S << endl;
		normalizeList(S);
		//cout << "Normalize = " << S << endl;
		Sum.signum = this->signum;
	} else {
		sign = -1;
		sumList(S, A, B, sign);
		//cout << "SubList = " << S << endl;
		sign = normalizeList(S);
		//cout << "Sub Normalize = " << S << endl;
		Sum.signum = this->signum * sign;
	
	}

	S.moveFront();
	if (S.length() == 1 && S.moveNext() == 0) {
		Sum.signum = 0;
	}
	return Sum;

}


// sub()
// Returns a BigInteger representing the difference of this and N.
BigInteger BigInteger::sub(const BigInteger& N) const
{
	BigInteger Sub = BigInteger(N);
	//cout << "R = " << Sub.digits << endl;
	//cout << "L = " << digits << endl;
	Sub.negate();
	//cout << Sub.signum << endl;
	return (this->add(Sub));
}

// mult()
// Returns a BigInteger representing the product of this and N. 
BigInteger BigInteger::mult(const BigInteger& N) const						//TA Mike Psuedo
{
	BigInteger Mult;
	List A = this->digits;
	List B = N.digits;
	List &M = Mult.digits;

	int shifts = 0;
	int sgn = 1;

	B.moveBack();
	while (B.position() > 0) {
		List C = A;
		ListElement b = B.movePrev();
		//cout << "movePrev: " << b << endl;
		//cout << "Befor SMult C = " << C << endl;
		scalarMultList(C, b);
		//cout << "SMult C = " << C << endl;
		//cout << "Befor shift C = " << C << endl;
		shiftList(C, shifts);
		//cout << "shift C = " << C << endl;

		//cout << "Befor Sum C = " << C << endl;
		sumList(M, M, C, sgn);
		//cout << "Add C = " << M << endl;
		//cout << "Befor Normal C = " << C << endl;
		normalizeList(M);
		shifts += 1;
	}

	Mult.signum = this->signum * N.signum;

	return Mult;
}


// Other Functions ---------------------------------------------------------

// to_string()
// Returns a string representation of this BigInteger consisting of its
// base 10 digits. If this BigInteger is negative, the returned string 
// will begin with a negative sign '-'. If this BigInteger is zero, the
// returned string will consist of the character '0' only.
std::string BigInteger::to_string()
{
	string s;

	if (signum == 0) {
		s.append("0");
	} else {
		digits.moveBack();
		while (digits.position() != 0) {
			ListElement x = digits.movePrev();
	        std::ostringstream ss;										//Mike Psuedo --> fills all remaining spots in POWER with 0's
	        ss << std::setw(POWER) << std::setfill('0') << x;
	        s = ss.str() + s;
		}

		while (s.length() > 1 && s[0] == '0') {				// TA Mike Psuedocode --> erases all leading 0's
			s.erase(0,1);
		}
	}

	if (signum == -1) {
		s.insert(0, "-");
	}

	return s;
}


// Overriden Operators -----------------------------------------------------

// operator<<()
// Inserts string representation of N into stream.
std::ostream& operator<<( std::ostream& stream, BigInteger N )
{
	return stream << N.BigInteger::to_string();
}

// operator==()
// Returns true if and only if A equals B. 
bool operator==( const BigInteger& A, const BigInteger& B )
{
	if (A.BigInteger::compare(B) == 0) {
		return true;
	} 
	return false;
}

// operator<()
// Returns true if and only if A is less than B. 
bool operator<( const BigInteger& A, const BigInteger& B )
{
	if (A.BigInteger::compare(B) == -1 ) {
		return true;
	} 
	return false;
}

// operator<=()
// Returns true if and only if A is less than or equal to B. 
bool operator<=( const BigInteger& A, const BigInteger& B )
{
	if (A.BigInteger::compare(B) == -1 || A.BigInteger::compare(B) == 0) {
		return true;
	} 
	return false;
}


// operator>()
// Returns true if and only if A is greater than B. 
bool operator>( const BigInteger& A, const BigInteger& B )
{
	if (A.BigInteger::compare(B) == 1) {
		return true;
	} 
	return false;
}


// operator>=()
// Returns true if and only if A is greater than or equal to B. 
bool operator>=( const BigInteger& A, const BigInteger& B )
{
	if (A.BigInteger::compare(B) == 1 || A.BigInteger::compare(B) == 0) {
		return true;
	} 
	return false;
}


// operator+()
// Returns the sum A+B. 
BigInteger operator+( const BigInteger& A, const BigInteger& B )
{
	return A.BigInteger::add(B);
}

// operator+=()
// Overwrites A with the sum A+B. 
BigInteger operator+=( BigInteger& A, const BigInteger& B )
{
	A = A.BigInteger::add(B);
	return A;
}

// operator-()
// Returns the difference A-B. 
BigInteger operator-( const BigInteger& A, const BigInteger& B )
{
	return A.BigInteger::sub(B);
}

// operator-=()
// Overwrites A with the difference A-B. 
BigInteger operator-=( BigInteger& A, const BigInteger& B )
{
	A = A.BigInteger::sub(B);
	return A;
}

// operator*()
// Returns the product A*B. 
BigInteger operator*( const BigInteger& A, const BigInteger& B )
{
	return A.BigInteger::mult(B);
}

// operator*=()
// Overwrites A with the product A*B. 
BigInteger operator*=( BigInteger& A, const BigInteger& B )
{
	A = A.BigInteger::mult(B);
	return A;
}



