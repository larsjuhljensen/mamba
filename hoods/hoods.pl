#!/usr/bin/perl

use strict;

###################################################################################
# Copyright (c) 2012-2013, Albert Palleja Caro & Lars Juhl Jensen                 #
# All rights reserved.                                                            #
#                                                                                 #
# Redistribution and use in source and binary forms, with or without              #
# modification, are permitted provided that the following conditions are met:     #
#     * Redistributions of source code must retain the above copyright            #
#       notice, this list of conditions and the following disclaimer.             #
#     * Redistributions in binary form must reproduce the above copyright         #
#       notice, this list of conditions and the following disclaimer in the       #
#       documentation and/or other materials provided with the distribution.      #
#     * Neither the name of the University of Copenhagen nor the                  #
#       names of its contributors may be used to endorse or promote products      #
#       derived from this software without specific prior written permission.     #
#                                                                                 #
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND #
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED   #
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE          #
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY              #
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES      #
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;    #
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND     #
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT      #
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS   #
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.                    #
###################################################################################

my $alpha = 0.8;
my $maxcluster;
my $maxentities;
if ($#ARGV < 4) {
	my %entities = ();
	open INT, "< $ARGV[0]";
	while (<INT>) {
		next if /^#/;
		s/^[ \t]+//;
		s/[ \t\r]*\n//;
		my ($entA, $entB, $score) = split /[ \t]+/;
		$entities{$entA} = 1;
		$entities{$entB} = 1;
	}
	close INT;
	my $count = scalar keys %entities;
	$maxcluster = sqrt($count);
	$maxcluster = 100 if $maxcluster < 100;
	$maxentities = 0.1*$count;
	$maxentities = 100 if $maxentities < 100;
}
$alpha = $ARGV[2] if $#ARGV >= 2;
$maxcluster = $ARGV[3] if $#ARGV >= 3;
$maxentities = $ARGV[4] if $#ARGV >= 4;

# Similarities between entities:
my %best_neighbors = ();
open (INT, "sort -k3nr $ARGV[0] |") || die "cannot open interactions: $!";
while (<INT>) {
	next if /^#/;
	s/^[ \t]+//;
	s/[ \t\r]*\n//;
	my ($entA, $entB, $score) = split /[ \t]+/;
	next if $entA eq $entB;
	$best_neighbors{$entA}{$entB} = $score unless exists $best_neighbors{$entA} and (exists $best_neighbors{$entA}{$entB} or scalar(keys %{$best_neighbors{$entA}}) >= $maxcluster);
	$best_neighbors{$entB}{$entA} = $score unless exists $best_neighbors{$entB} and (exists $best_neighbors{$entB}{$entA} or scalar(keys %{$best_neighbors{$entB}}) >= $maxcluster);
}
close INT;

my %scores = ();
open (SCORES, "< $ARGV[1]") || die "cannot open scores: $!";
while (<SCORES>) {
	next if /^#/;
	s/^[ \t]+//;
	s/[ \t\r]*\n//;
	my ($entity, $score) = split /[ \t]+/;
	$score = 1 unless defined $score;
	$scores{$entity} = $score if $score > 0;
}
close SCORES;

# Building neighborhoods and printing them:
my %network_scores = ();
my %network_entities = ();
foreach my $entity (keys %best_neighbors) {
	my @entities = sort {$best_neighbors{$entity}{$b} <=> $best_neighbors{$entity}{$a}} keys %{$best_neighbors{$entity}};
	unshift (@entities, $entity);
	my @ent_with_score = ();
	my $count = 0;
	my $sum = 0;
	foreach my $ent (@entities) {
		$count++;
		next unless exists $scores{$ent};
		push @ent_with_score, $ent;
		$sum += $scores{$ent};
		next unless scalar(@ent_with_score) > 1;
		my $seeds = join(",", sort @ent_with_score);
		my $score = $sum/($count**$alpha);
		next if exists $network_scores{$seeds} and $network_scores{$seeds} >= $score;
		$network_scores{$seeds} = $score;
		$network_entities{$seeds} = join(",", @entities[0..($count-1)]);
	}
}

print "Score\tSize\tNodes\n";
my %entities_seen = ();
foreach my $seeds (sort { $network_scores{$b} <=> $network_scores{$a} } keys %network_scores) {
	my @entities = split /\,/, $network_entities{$seeds};
	my $print = 0;
	foreach my $entity (@entities) {
		next if exists $entities_seen{$entity};
		$entities_seen{$entity} = 1;
		$print = 1;
	}
	printf "%.3f\t%d\t%s\n", $network_scores{$seeds}, scalar(@entities), join(" ", sort @entities) if $print;
	last if scalar(keys %entities_seen) >= $maxentities;
}
