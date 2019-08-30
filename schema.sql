create table if not exists train_log (
  created timestamp not NULL,
  actual text not NULL,
  guess text not NULL
);