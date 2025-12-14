// Project the course prerequisite graph in memory
CALL gds.graph.project(
  'courseGraph',
  'Course',
  {
    PRE_REQUIRES: {
      orientation: 'NATURAL'
    }
  }
);

