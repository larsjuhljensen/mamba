#!/usr/bin/perl -w

use strict;

die "Syntax: $0 regex fastafile\n" unless scalar @ARGV == 2;

my $regex = $ARGV[0];
my $fasta = $ARGV[1];

sub search
{
  if ($_[0] ne "") {
    $_[1] =~ s/($_[2])/print $_[0],"\t",$-[0]+1,"\t",$+[0],"\t",$1,"\n"; $1/eg;
  }
}

print "Name\tStart\tEnd\tMatch\n";

my $name = "";
my $sequence = "";
open FASTA, "< $fasta";
while (<FASTA>) {
  s/\r?\n//;
  if (/^>([^ \t\r\n]*)/) {
    search($name, $sequence, $regex);
    $name = $1;
    $sequence = "";
  }
  else {
    $sequence .= $_;
  }
}
search($name, $sequence, $regex);
close FASTA;