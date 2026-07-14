#include<iostream>
#include<fstream>
#include<string>

#include "BigInteger.h"

using namespace std;

#define MAX_LEN 300

int main(int argc, char * argv[]){

	ifstream in;
	ofstream out;

	string a;
	string empty;
	string b;

	 // check command line for correct number of arguments
	if( argc != 3 ){
		cerr << "Usage: " << argv[0] << " <input file> <output file>" << endl;
		return(EXIT_FAILURE);
	}

	// open files for reading and writing 
	in.open(argv[1]);
	if( !in.is_open() ){
		cerr << "Unable to open file " << argv[1] << " for reading" << endl;
		return(EXIT_FAILURE);
	}

	out.open(argv[2]);
	if( !out.is_open() ){
		cerr << "Unable to open file " << argv[2] << " for writing" << endl;
		return(EXIT_FAILURE);
	}


	getline(in, a);
	getline(in, empty);
	getline(in, b);

	BigInteger A = BigInteger(a);
	BigInteger B = BigInteger(b);

	out << A << endl;
	out << endl;
	out << B << endl;
	out << endl;
	out << A+B << endl;
	out << endl;
	out << A-B << endl;
	out << endl;
	out << A-A << endl;
	out << endl;
	BigInteger H = BigInteger("3");
	BigInteger T = BigInteger("2");
	out << ((H*A) - (T*B)) << endl;
	out << endl;
	out << A*B << endl;
	out << endl;
	out << A*A << endl;
	out << endl;
	out << B*B << endl;
	out << endl;
	BigInteger N = BigInteger("9");
	BigInteger S = BigInteger("16");

	out << ((N*(A*A*A*A)) + (S*(B*B*B*B*B))) << endl;

	in.close();
	out.close();


	return 0;

}

